import cv2 # Added
import asyncio # Added
from starlette.websockets import WebSocketDisconnect # Added
from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from .user_auth_backend import get_current_user
from .dashboard_backend import router as api_router
from .user_auth_backend import auth_router
from .config import settings
from .camera_manager import CameraManager
from .database import SessionLocal, init_db # Added init_db import

print("Initializing database (if needed)...")
init_db() # Call to create tables based on models
print("Database initialization check complete.")

app = FastAPI(title="SecurityCam Suite API")

# Global CameraManager instance
# This session is dedicated to the CameraManager's lifetime
db_session_for_camera_manager = SessionLocal() 
camera_manager_global = CameraManager(db_session=db_session_for_camera_manager)

@app.on_event("shutdown")
def shutdown_event():
    print("Application shutdown: Releasing camera resources...")
    camera_manager_global.shutdown()
    db_session_for_camera_manager.close()
    print("CameraManager shut down and its DB session closed.")

# Dependency to provide the CameraManager instance
def get_camera_manager_dependency():
    return camera_manager_global

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS, # Use settings
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

app.include_router(api_router) # This has /api prefix from its own file
app.include_router(auth_router, tags=["Authentication"]) # Routes in auth_router already have /auth

@app.websocket("/ws/stream/{camera_id}")
async def stream_endpoint(
    websocket: WebSocket, 
    camera_id: str, 
    user = Depends(get_current_user), # Assuming get_current_user is configured
    cm: CameraManager = Depends(get_camera_manager_dependency) # Get CameraManager via dependency
):
    await websocket.accept()
    
    try:
        int_camera_id = int(camera_id)
    except ValueError:
        # Send an error message and close if camera_id is not a valid integer
        await websocket.send_text("Error: Invalid camera ID format.")
        await websocket.close(code=1008) # Policy Violation
        return

    managed_cam = cm.get_camera(int_camera_id)
    if not managed_cam or not managed_cam.is_running:
        await websocket.send_text(f"Error: Camera {int_camera_id} not found or not active.")
        await websocket.close(code=1011) # Internal Error
        return

    # Determine FPS for streaming
    # Use camera's configured FPS if available, else a default (e.g., 30 FPS)
    stream_fps = 30 # Default
    if managed_cam.settings and hasattr(managed_cam.settings, 'frame_rate') and managed_cam.settings.frame_rate:
        stream_fps = managed_cam.settings.frame_rate
    
    frame_interval = 1.0 / stream_fps

    try:
        while True:
            frame = cm.get_frame_from_camera(int_camera_id) # This gets the processed frame
            
            if frame is not None:
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ret:
                    await websocket.send_bytes(buffer.tobytes())
                else:
                    # Log if encoding fails, but continue loop or send error?
                    print(f"[WebSocket Stream {int_camera_id}] Frame encoding failed.")
            else:
                # Camera might be temporarily unavailable or stopped.
                # If camera permanently stops, get_frame_from_camera might return None consistently.
                # Check if the camera is still supposed to be running
                current_cam_state = cm.get_camera(int_camera_id)
                if not current_cam_state or not current_cam_state.is_running:
                    print(f"[WebSocket Stream {int_camera_id}] Camera stopped. Closing stream.")
                    break # Exit loop if camera is no longer running
                # If still running but frame is None, it might be a temporary issue.
                # print(f"[WebSocket Stream {int_camera_id}] Frame is None, but camera still running. Pausing.")
                pass


            await asyncio.sleep(frame_interval) # Regulate frame rate

    except WebSocketDisconnect:
        print(f"[WebSocket Stream {int_camera_id}] Client disconnected.")
    except Exception as e:
        print(f"[WebSocket Stream {int_camera_id}] Error: {e}")
        try:
            await websocket.send_text(f"Streaming error: {str(e)}") # Try to inform client
        except Exception: # Could fail if socket already closed
            pass
    finally:
        print(f"[WebSocket Stream {int_camera_id}] Closing WebSocket.")
        # FastAPI handles closing on context exit or if an unhandled exception propagates.
        # No explicit websocket.close() here to avoid errors if already closed.
        pass