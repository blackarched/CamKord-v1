dashboard_backend.py

import os
import cv2
import time
import asyncio
import io
from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, FastAPI, Depends, HTTPException, Request, status, Query
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse # Added FileResponse
from sqlalchemy.orm import Session

from database import SessionLocal, init_db
from database import User as DBUser, EventLog, CameraSettings as DBCameraSettings, Camera as DBCamera # Added DBCamera, aliased User
from .user_auth_backend import get_current_user
from .camera_manager import CameraManager
from .main import get_camera_manager_dependency, limiter
from .schemas import CameraSettingsUpdate, CameraInfo, CameraSettingsResponse, CameraCreate, CameraResponse, CameraUpdate, RecordingInfo # Added RecordingInfo
from .config import settings
from .crypto_utils import get_fernet_instance, encrypt_data, decrypt_data

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

@router.post(
    "/admin/cameras/",
    response_model=CameraResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Admin - Cameras"]
)
def create_new_camera_admin(
    camera_data: CameraCreate,
    db: Session = Depends(get_db),
    current_admin_user: DBUser = Depends(get_current_user),
    cm: CameraManager = Depends(get_camera_manager_dependency)
):
    if not current_admin_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted: Requires admin privileges."
        )

    if camera_data.name:
        existing_camera_name = db.query(DBCamera).filter(DBCamera.name == camera_data.name).first()
        if existing_camera_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Camera name '{camera_data.name}' already exists."
            )
    if camera_data.rtsp_url:
        existing_camera_url = db.query(DBCamera).filter(DBCamera.rtsp_url == camera_data.rtsp_url).first()
        if existing_camera_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"RTSP URL '{camera_data.rtsp_url}' is already in use."
            )

    db_camera = DBCamera(
        name=camera_data.name,
        location=camera_data.location,
        rtsp_url=camera_data.rtsp_url,
        is_active=camera_data.is_active
    )
    db.add(db_camera)
    db.commit()

    default_settings = DBCameraSettings(
        camera_id=db_camera.id,
        resolution= "1280x720",
        night_vision=False,
        autofocus=True,
        brightness=50,
        contrast=50,
        saturation=50,
        sharpness=50,
        microphone_enabled=True,
        motion_detection_enabled=False,
        motion_sensitivity=30,
        motion_min_area=500,
        record_on_motion=False,
        object_detection_enabled=False
    )
    db.add(default_settings)
    db.commit()
    db.refresh(db_camera)

    if db_camera.is_active:
        cm.reload_cameras_from_db()

    return db_camera

@router.put(
    "/admin/cameras/{camera_id}",
    response_model=CameraResponse,
    tags=["Admin - Cameras"]
)
def update_camera_admin(
    camera_id: int,
    camera_update_data: CameraUpdate, # Uses CameraUpdate schema for request body
    db: Session = Depends(get_db),
    current_admin_user: DBUser = Depends(get_current_user),
    cm: CameraManager = Depends(get_camera_manager_dependency)
):
    if not current_admin_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted: Requires admin privileges."
        )

    db_camera = db.query(DBCamera).filter(DBCamera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Camera with ID {camera_id} not found.")

    update_data = camera_update_data.dict(exclude_unset=True) # Only get fields that were actually sent

    # Check for potential duplicate name if 'name' is in update_data and is different
    if 'name' in update_data and update_data['name'] != db_camera.name:
        existing_camera_name = db.query(DBCamera).filter(DBCamera.name == update_data['name'], DBCamera.id != camera_id).first()
        if existing_camera_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Another camera with the name '{update_data['name']}' already exists."
            )

    # Check for potential duplicate RTSP URL if 'rtsp_url' is in update_data, is not None, and is different
    if 'rtsp_url' in update_data and update_data.get('rtsp_url') and update_data['rtsp_url'] != db_camera.rtsp_url:
        existing_camera_url = db.query(DBCamera).filter(DBCamera.rtsp_url == update_data['rtsp_url'], DBCamera.id != camera_id).first()
        if existing_camera_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Another camera with the RTSP URL '{update_data['rtsp_url']}' already exists."
            )

    # Apply updates
    for field, value in update_data.items():
        if hasattr(db_camera, field):
            setattr(db_camera, field, value)

    db.add(db_camera)
    db.commit()
    db.refresh(db_camera)

    cm.reload_cameras_from_db()

    return db_camera

@router.delete(
    "/admin/cameras/{camera_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Admin - Cameras"]
)
def delete_camera_admin(
    camera_id: int,
    db: Session = Depends(get_db),
    current_admin_user: DBUser = Depends(get_current_user),
    cm: CameraManager = Depends(get_camera_manager_dependency)
):
    if not current_admin_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted: Requires admin privileges."
        )

    db_camera = db.query(DBCamera).filter(DBCamera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Camera with ID {camera_id} not found.")

    managed_cam = cm.get_camera(camera_id)
    if managed_cam:
        print(f"[Admin Delete] Camera {camera_id} found in CameraManager. Releasing its resources.")
        managed_cam.release()

    # Delete the camera from the database.
    # Associated CameraSettings and EventLogs should be deleted automatically
    # due to "cascade='all, delete-orphan'" on the relationships in DBCamera model.
    db.delete(db_camera)
    db.commit()

    print(f"Camera {camera_id} and its associated settings/logs (due to cascade) deleted from database.")

    cm.reload_cameras_from_db()

    return None

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

@router.get("/recordings", response_model=List[RecordingInfo], tags=["Recordings"])
# @limiter.limit("120/minute") # Example: if specific rate limit needed
def list_recordings(
    request: Request, # Required by limiter, good to have for extensions
    camera_id_filter: Optional[int] = Query(None, description="Filter by camera ID", alias="camera_id"),
    date_start_filter: Optional[date] = Query(None, description="Filter by start date (YYYY-MM-DD)", alias="date_start"),
    date_end_filter: Optional[date] = Query(None, description="Filter by end date (YYYY-MM-DD)", alias="date_end"),
    db: Session = Depends(get_db), # To fetch camera names
    current_user: DBUser = Depends(get_current_user) # Authentication
):
    recordings_list = []
    recording_dir = settings.RECORDING_DIR

    if not os.path.exists(recording_dir) or not os.path.isdir(recording_dir):
        print(f"Warning: Recording directory '{recording_dir}' not found or is not a directory.")
        return [] # Return empty list if directory doesn't exist

    # Fetch all camera names once for efficient lookup
    cameras_db = db.query(DBCamera.id, DBCamera.name).all()
    camera_name_map = {cam_id: cam_name for cam_id, cam_name in cameras_db}

    try:
        filenames = os.listdir(recording_dir)
    except OSError as e:
        print(f"Error listing recording directory '{recording_dir}': {e}")
        raise HTTPException(status_code=500, detail="Could not read recordings directory.")

    for filename in filenames:
        if not filename.lower().endswith(".mp4"): # Case-insensitive check for .mp4
            continue

        file_path = os.path.join(recording_dir, filename)

        try:
            if not os.path.isfile(file_path): # Ensure it's a file
                continue

            stat_info = os.stat(file_path)
            file_size_bytes = stat_info.st_size
            file_mtime = datetime.fromtimestamp(stat_info.st_mtime)

            # Apply date filtering (inclusive)
            if date_start_filter and file_mtime.date() < date_start_filter:
                continue
            if date_end_filter and file_mtime.date() > date_end_filter:
                continue

            parsed_cam_id: Optional[int] = None
            # Try to parse camera ID from filename format: rec_cam<ID>_<timestamp>.mp4
            if filename.startswith("rec_cam") and "_" in filename:
                parts = filename.split("_")
                if len(parts) > 1 and parts[1].startswith("cam"):
                    cam_id_str = parts[1][3:] # Remove "cam" prefix
                    if cam_id_str.isdigit():
                        parsed_cam_id = int(cam_id_str)

            # Apply camera_id filter
            if camera_id_filter is not None and parsed_cam_id != camera_id_filter:
                continue

            camera_name = camera_name_map.get(parsed_cam_id) if parsed_cam_id is not None else "Unknown"

            recordings_list.append(
                RecordingInfo(
                    filename=filename,
                    size=file_size_bytes,
                    timestamp=file_mtime,
                    camera_id=parsed_cam_id,
                    camera_name=camera_name
                )
            )
        except FileNotFoundError:
            # File might have been deleted by another process between listdir and stat
            print(f"Warning: File '{filename}' vanished during processing, skipping.")
            continue
        except Exception as e:
            # Catch other potential errors during file processing
            print(f"Error processing recording file '{filename}': {e}")
            continue

    # Sort recordings by timestamp, newest first
    recordings_list.sort(key=lambda r: r.timestamp, reverse=True)

    return recordings_list

@router.get(
    "/recordings/view/{filename}",
    response_class=FileResponse,
    tags=["Recordings"],
    summary="Stream or download a specific recording file.",
    description="Serves a video recording file. Requires authentication. " \
                "Filename should be a valid .mp4 file found in the recordings directory. " \
                "Clients (like HTML5 video player) can use this endpoint for streaming playback."
)
async def view_recording_file(
    filename: str,
    request: Request,
    current_user: DBUser = Depends(get_current_user)
):
    if ".." in filename or filename.startswith(("/", "\\")) or not filename.lower().endswith(".mp4"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename. Must be a .mp4 file and not contain path traversal elements."
        )

    file_path = os.path.join(settings.RECORDING_DIR, filename)

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        print(f"Recording file not found at path: {file_path}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Recording '{filename}' not found.")

    print(f"User '{current_user.username}' (ID: {current_user.id}) is accessing recording: {filename}")

    return FileResponse(
        path=file_path,
        media_type="video/mp4",
        filename=filename
    )

@router.delete(
    "/recordings/{filename}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Recordings"],
    summary="Delete a specific recording file.",
    description="Deletes a video recording file from the server's storage. Requires admin privileges."
)
async def delete_recording_file(
    filename: str,
    request: Request,
    current_admin_user: DBUser = Depends(get_current_user),
    cm: CameraManager = Depends(get_camera_manager_dependency)
):
    if not current_admin_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted: Requires admin privileges."
        )

    if ".." in filename or filename.startswith(("/", "\\")) or not filename.lower().endswith(".mp4"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename. Must be an .mp4 file and not contain path traversal elements."
        )

    file_path = os.path.join(settings.RECORDING_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Recording '{filename}' not found.")

    if not os.path.isfile(file_path):
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"'{filename}' is not a valid file.")

    parsed_cam_id: Optional[int] = None
    if filename.startswith("rec_cam") and "_" in filename:
        parts = filename.split("_")
        if len(parts) > 1 and parts[1].startswith("cam"):
            cam_id_str = parts[1][3:]
            if cam_id_str.isdigit():
                parsed_cam_id = int(cam_id_str)

    try:
        os.remove(file_path)
        print(f"User '{current_admin_user.username}' (ID: {current_admin_user.id}) deleted recording: {filename}")

        cm.record_camera_event(
            camera_id=parsed_cam_id,
            event_type="recording_deleted",
            description=f"File: {filename} deleted by admin '{current_admin_user.username}'."
        )

        return None

    except OSError as e:
        error_message = f"Could not delete recording '{filename}': {e.strerror} (OS Error {e.errno})"
        print(f"[Delete Recording Error] {error_message}")
        cm.record_camera_event(
            camera_id=parsed_cam_id,
            event_type="recording_delete_failed",
            description=f"Attempt by admin '{current_admin_user.username}' to delete file: {filename}. Error: {e.strerror}"
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_message)
    except Exception as e:
        error_message = f"An unexpected error occurred while deleting recording '{filename}': {str(e)}"
        print(f"[Delete Recording Error] {error_message}")
        cm.record_camera_event(
            camera_id=parsed_cam_id,
            event_type="recording_delete_failed",
            description=f"Attempt by admin '{current_admin_user.username}' to delete file: {filename}. Error: {str(e)}"
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_message)

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
