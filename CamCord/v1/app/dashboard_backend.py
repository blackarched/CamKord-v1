dashboard_backend.py

import os
import cv2
import time
import asyncio
import io # Added for StreamingResponse
from typing import List, Optional
from fastapi import APIRouter, FastAPI, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session

from database import SessionLocal, init_db # init_db call is commented out below
from database import User, EventLog, CameraSettings as DBCameraSettings # Ensure DBCameraSettings is imported
from .user_auth_backend import get_current_user
from .camera_manager import CameraManager
from .main import get_camera_manager_dependency, limiter
from .schemas import CameraSettingsUpdate, CameraInfo, CameraSettingsResponse
from .config import settings
from .crypto_utils import get_fernet_instance, encrypt_data, decrypt_data # Added decrypt_data

# --- Initialize database ---
# init_db() # This should ideally be called once at startup, e.g. in main.py, not here.
            # For now, assuming it's handled or if this module is run standalone.

# --- Global Camera Manager ---
# camera_manager = CameraManager() # Removed: Now injected via dependency

# --- Router Setup ---
router = APIRouter(prefix="/api")

# --- Dependency ---
def get_db() -> Session: # This is a general DB session, CameraManager has its own.
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Removed ObjectDetector and object_detection_stream ---

# --- API Endpoints ---

@router.get('/cameras', tags=['Cameras'], response_model=List[CameraInfo])
def list_cameras(
    user=Depends(get_current_user),
    cm: CameraManager = Depends(get_camera_manager_dependency)
):
    managed_cams = cm.get_all_cameras()
    cameras_info = []
    for cam in managed_cams:
        cam_info = CameraInfo(
            id=cam.camera_id,
            name=cam.name,
            rtsp_url=cam.rtsp_url,
            is_running=cam.is_running,
            motion_detection_enabled=cam.settings.motion_detection_enabled if cam.settings else None,
            object_detection_enabled=cam.settings.object_detection_enabled if cam.settings else None
        )
        cameras_info.append(cam_info)
    return cameras_info

# Removed old /cameras/{camera_id}/feed

@router.get("/cameras/{camera_id}/mjpeg_feed", tags=["Cameras"], include_in_schema=False)
async def mjpeg_camera_feed(
    camera_id: int,
    user = Depends(get_current_user),
    cm: CameraManager = Depends(get_camera_manager_dependency)
):
    managed_cam = cm.get_camera(camera_id)
    if not managed_cam or not managed_cam.is_running:
        raise HTTPException(status_code=404, detail="Camera not found or not running")

    async def frame_generator():
        last_frame_time = time.time()
        # Target FPS can be read from camera settings if available, e.g. managed_cam.settings.frame_rate
        frame_interval = 1.0 / (managed_cam.settings.frame_rate if hasattr(managed_cam.settings, 'frame_rate') and managed_cam.settings.frame_rate else 30.0)

        while True:
            # Check if camera is still managed and running; could be stopped externally
            current_managed_cam = cm.get_camera(camera_id)
            if not current_managed_cam or not current_managed_cam.is_running:
                print(f"Camera {camera_id} stopped or removed. Closing MJPEG stream.")
                break # Exit the loop to stop the generator

            frame = cm.get_frame_from_camera(camera_id) # This already applies settings
            if frame is not None:
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80]) # Added quality param
                if ret:
                    jpeg_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg_bytes + b'\r\n')

            current_time = time.time()
            elapsed = current_time - last_frame_time
            wait_time = frame_interval - elapsed

            if wait_time > 0:
                await asyncio.sleep(wait_time)
            last_frame_time = time.time() # Update last_frame_time regardless of sleep

            # Yield a very small amount of time to prevent tight loop if processing is faster than interval
            if wait_time <= 0:
                 await asyncio.sleep(0.001)


    return StreamingResponse(frame_generator(), media_type='multipart/x-mixed-replace; boundary=frame')

@router.get('/events', tags=['Logs'])
def get_events(limit: int = 100, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # Ensure EventLog model is imported correctly. It is.
    # message column was renamed to event_description in database.py for EventLog model
    events = db.query(EventLog).order_by(EventLog.timestamp.desc()).limit(limit).all()
    return [{'timestamp': e.timestamp, 'camera_id': e.camera_id, 'type': e.event_type, 'message': e.event_description} for e in events] # Changed e.message to e.event_description

@router.get('/settings/{camera_id}', tags=['Settings'], response_model=CameraSettingsResponse)
def get_camera_settings(camera_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # Assuming camera_id in CameraSettings is now an Integer ForeignKey
    settings = db.query(DBCameraSettings).filter(DBCameraSettings.camera_id == camera_id).first()
    if not settings:
        raise HTTPException(status_code=404, detail='Settings not found for this camera ID')
    # Pydantic models for response are better, but .dict might be from SQLAlchemy model if it has it.
    # If DBCameraSettings is a SQLAlchemy model, direct return is fine, FastAPI handles it.
    # The 'settings.dict' in the original code might be from a Pydantic model.
    # For SQLAlchemy model, we should use a Pydantic response_model or return the object itself.
    # For now, returning the object. Schemas will handle serialization.
    return settings

@router.post('/settings/{camera_id}', tags=['Settings'], response_model=CameraSettingsResponse)
@limiter.limit("60/minute")
def update_camera_settings(
    request: Request, # Added request
    camera_id: int,
    settings_update_data: CameraSettingsUpdate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
    cm: CameraManager = Depends(get_camera_manager_dependency)
):
    record = db.query(DBCameraSettings).filter(DBCameraSettings.camera_id == camera_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Settings not found for this camera ID, cannot update.")

    update_data = settings_update_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(record, field): # Ensure the field exists on the SQLAlchemy model
            setattr(record, field, value)

    db.commit()
    db.refresh(record)

    # Notify the camera manager that this camera's settings have changed
    if record: # Ensure record is not None before accessing camera_id
        cm.notify_settings_updated(camera_id=record.camera_id, db_session_for_reload=db)

    return record # Return the updated record

@router.post("/cameras/{camera_id}/snapshot", tags=["Cameras"])
@limiter.limit("30/minute")
async def take_camera_snapshot(
    request: Request, # Added request
    camera_id: int,
    user = Depends(get_current_user),
    cm: CameraManager = Depends(get_camera_manager_dependency)
):
    frame = cm.get_frame_from_camera(camera_id)
    if frame is None:
        raise HTTPException(status_code=404, detail="Camera offline or unable to capture frame")

    try:
        os.makedirs(settings.SNAPSHOT_DIR, exist_ok=True)

        fernet_instance = get_fernet_instance(settings.DATA_ENCRYPTION_KEY)
        timestamp_str = str(int(time.time()))
        saved_filename = ""
        is_encrypted = False
        file_path_to_return = "" # Initialize to ensure it's always defined

        if fernet_instance:
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            if not ret:
                raise HTTPException(status_code=500, detail="Failed to encode frame to JPEG for encryption")

            image_bytes = buffer.tobytes()
            encrypted_bytes = encrypt_data(image_bytes, fernet_instance)

            if encrypted_bytes:
                saved_filename = f"enc_snapshot_cam{camera_id}_{timestamp_str}.jpg.enc"
                file_path = os.path.join(settings.SNAPSHOT_DIR, saved_filename)
                with open(file_path, 'wb') as f:
                    f.write(encrypted_bytes)
                print(f"Encrypted snapshot saved: {file_path}")
                is_encrypted = True
                cm.record_camera_event(camera_id=camera_id, event_type="snapshot_encrypted", description=f"Snapshot saved (encrypted): {saved_filename}")
                file_path_to_return = file_path
            else:
                print("Warning: Encryption failed. Saving snapshot unencrypted.")
                saved_filename = f"snapshot_cam{camera_id}_{timestamp_str}.jpg"
                file_path = os.path.join(settings.SNAPSHOT_DIR, saved_filename)
                if not cv2.imwrite(file_path, frame):
                     raise HTTPException(status_code=500, detail="Failed to save unencrypted snapshot after encryption failure")
                cm.record_camera_event(camera_id=camera_id, event_type="snapshot_unencrypted_fallback", description=f"Snapshot (unencrypted, encryption failed): {saved_filename}")
                file_path_to_return = file_path
        else:
            print("Warning: DATA_ENCRYPTION_KEY not set. Saving snapshot unencrypted.")
            saved_filename = f"snapshot_cam{camera_id}_{timestamp_str}.jpg"
            file_path = os.path.join(settings.SNAPSHOT_DIR, saved_filename)
            if not cv2.imwrite(file_path, frame):
                raise HTTPException(status_code=500, detail="Failed to save unencrypted snapshot")
            cm.record_camera_event(camera_id=camera_id, event_type="snapshot_unencrypted_key_missing", description=f"Snapshot (unencrypted, key N/A): {saved_filename}")
            file_path_to_return = file_path

        view_url = f"/api/snapshots/view/{saved_filename}" if is_encrypted else None
        return JSONResponse(content={
            "message": "Snapshot processed",
            "filename": saved_filename,
            "filepath": file_path_to_return, # This is server path
            "encrypted": is_encrypted,
            "view_url": view_url
        })
    except Exception as e:
        print(f"Error processing snapshot for camera {camera_id}: {e}")
        # Ensure cm is available for event recording even in exception
        if 'cm' in locals() and hasattr(cm, 'record_camera_event'):
            cm.record_camera_event(camera_id=camera_id, event_type="snapshot_failed", description=f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing snapshot: {str(e)}")

@router.get("/snapshots/view/{filename_enc}", tags=["Snapshots"], response_class=StreamingResponse)
async def view_encrypted_snapshot(
    filename_enc: str,
    request: Request,
    current_user = Depends(get_current_user),
):
    # Validate filename to prevent directory traversal
    if ".." in filename_enc or filename_enc.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid filename.")

    file_path = os.path.join(settings.SNAPSHOT_DIR, filename_enc)

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Encrypted snapshot not found.")

    fernet_instance = get_fernet_instance(settings.DATA_ENCRYPTION_KEY)
    if not fernet_instance:
        print(f"Snapshot Decryption Error: DATA_ENCRYPTION_KEY not configured or invalid. Cannot decrypt {filename_enc}.")
        raise HTTPException(status_code=500, detail="Snapshot decryption service misconfigured.")

    try:
        with open(file_path, 'rb') as f:
            encrypted_content = f.read()
    except Exception as e:
        print(f"Error reading encrypted snapshot file {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Error reading snapshot file.")

    decrypted_bytes = decrypt_data(encrypted_content, fernet_instance)
    if decrypted_bytes is None:
        print(f"Failed to decrypt snapshot {filename_enc}. Token might be invalid or data corrupted.")
        # Consider logging this event via CameraManager if applicable, e.g.:
        # cm.record_camera_event(camera_id=None, event_type="snapshot_decrypt_failed", description=f"Failed for file: {filename_enc}")
        raise HTTPException(status_code=500, detail="Snapshot decryption failed. File may be corrupt or key incorrect.")

    return StreamingResponse(io.BytesIO(decrypted_bytes), media_type="image/jpeg")

@router.post("/cameras/{camera_id}/recording/start", tags=["Cameras"])
@limiter.limit("15/minute")
async def start_camera_recording_api(
    request: Request, # Added request
    camera_id: int,
    user = Depends(get_current_user),
    cm: CameraManager = Depends(get_camera_manager_dependency)
):
    managed_cam = cm.get_camera(camera_id)
    if not managed_cam or not managed_cam.is_running: # Check if camera is active
        raise HTTPException(status_code=404, detail="Camera not found or not currently running")
    if managed_cam.is_recording:
        return JSONResponse(content={"message": "Camera is already recording"}, status_code=400)

    if managed_cam.start_recording():
        return JSONResponse(content={"message": "Recording started successfully"})
    else:
        # Generic error if start_recording returned False for other reasons (e.g., can't get frame)
        raise HTTPException(status_code=500, detail="Failed to start recording. Check server logs.")

@router.post("/cameras/{camera_id}/recording/stop", tags=["Cameras"])
@limiter.limit("15/minute")
async def stop_camera_recording_api(
    request: Request, # Added request
    camera_id: int,
    user = Depends(get_current_user),
    cm: CameraManager = Depends(get_camera_manager_dependency)
):
    managed_cam = cm.get_camera(camera_id)
    if not managed_cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    if not managed_cam.is_recording:
            return JSONResponse(content={"message": "Camera is not currently recording"}, status_code=400)

    if managed_cam.stop_recording():
        return JSONResponse(content={"message": "Recording stopped successfully"})
    else:
        # This case might be rare if stop_recording is robust
        raise HTTPException(status_code=500, detail="Failed to stop recording cleanly. Check server logs.")

--- Application Mounting ---
# The following app instance is for standalone running of this dashboard,
# but it's not used when main.py is the entry point.
# Consider removing or conditionalizing it further if this file is only a router module.
_dashboard_standalone_app = FastAPI(title='SecurityCam Dashboard API (Standalone)')
_dashboard_standalone_app.include_router(router)

@_dashboard_standalone_app.get('/health_standalone') # Differentiate health check path
def health_standalone():
    return {'status': 'ok'}

# if name == 'main':
#     # Launch with: uvicorn dashboard_backend:_dashboard_standalone_app --host 0.0.0.0 --port 8001
#     import uvicorn
#     uvicorn.run(_dashboard_standalone_app, host='0.0.0.0', port=8001) # Removed reload=False for dev
