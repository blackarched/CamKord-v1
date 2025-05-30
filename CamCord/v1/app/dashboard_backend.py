dashboard_backend.py

import os
import cv2
import time
import asyncio
from typing import List, Optional # Generator removed
from fastapi import APIRouter, FastAPI, Depends, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session

from database import SessionLocal, init_db # init_db call is commented out below
from database import User, EventLog, CameraSettings as DBCameraSettings # Ensure DBCameraSettings is imported
from .user_auth_backend import get_current_user
from .camera_manager import CameraManager # For type hinting
from .main import get_camera_manager_dependency
from .schemas import CameraSettingsUpdate, CameraInfo, CameraSettingsResponse # Updated imports
from .config import settings # Added for SNAPSHOT_DIR

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
def update_camera_settings(
    camera_id: int, 
    settings_update_data: CameraSettingsUpdate,
    db: Session = Depends(get_db), 
    user = Depends(get_current_user),
    cm: CameraManager = Depends(get_camera_manager_dependency) # Added CameraManager dependency
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
async def take_camera_snapshot(
    camera_id: int,
    user = Depends(get_current_user),
    cm: CameraManager = Depends(get_camera_manager_dependency)
):
    frame = cm.get_frame_from_camera(camera_id)
    if frame is None:
        raise HTTPException(status_code=404, detail="Camera offline or unable to capture frame")

    try:
        # Ensure snapshot directory exists
        os.makedirs(settings.SNAPSHOT_DIR, exist_ok=True)
        
        # Create a unique filename
        filename = f"snapshot_cam{camera_id}_{int(time.time())}.jpg"
        file_path = os.path.join(settings.SNAPSHOT_DIR, filename)
        
        # Save the frame
        success = cv2.imwrite(file_path, frame)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save snapshot")

        # TODO: Consider adding an EventLog entry here - Addressed
        print(f"Snapshot saved: {file_path}") # Basic logging
        cm.record_camera_event(camera_id=camera_id, event_type="snapshot_taken", description=f"Snapshot taken: {filename}")

        return JSONResponse(content={"message": "Snapshot saved", "filename": filename, "filepath": file_path})
    except Exception as e:
        print(f"Error taking snapshot: {e}")
        raise HTTPException(status_code=500, detail=f"Error taking snapshot: {str(e)}")

@router.post("/cameras/{camera_id}/recording/start", tags=["Cameras"])
async def start_camera_recording_api(
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
async def stop_camera_recording_api(
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

