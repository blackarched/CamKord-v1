import cv2
import asyncio
from starlette.websockets import WebSocketDisconnect
from fastapi import FastAPI, WebSocket, Depends, Query # Added Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session # Added Session
from jose import JWTError, jwt # Added jose imports

from .user_auth_backend import get_current_user # This is for HTTP routes
from .user_auth_backend import TokenData, get_db as get_user_auth_db_session # For WS auth
from .dashboard_backend import router as api_router
from .user_auth_backend import auth_router
from .config import settings
from .camera_manager import CameraManager
from .database import SessionLocal, init_db, User as DBUser
from typing import Optional
import os # Added
from fastapi.staticfiles import StaticFiles # Added
from fastapi import HTTPException # Added (for potential explicit error raising)


print("Initializing database (if needed)...")
init_db() # Call to create tables based on models
print("Database initialization check complete.")

# WebSocket Authentication Dependency
async def get_current_user_from_ws_token(
    token: Optional[str] = Query(None), 
    db: Session = Depends(get_user_auth_db_session)
) -> Optional[DBUser]:
    if token is None:
        print("[WS Auth] No token provided in query.")
        return None 
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            print("[WS Auth] Token payload missing 'sub' (username).")
            return None
        # TokenData might not be strictly needed if just using username from payload
        # token_data = TokenData(username=username) 
    except JWTError as e:
        print(f"[WS Auth] JWTError: {e}")
        return None # Invalid token

    user = db.query(DBUser).filter(DBUser.username == username).first()
    if user is None:
        print(f"[WS Auth] User '{username}' not found in DB.")
    return user

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
    # user = Depends(get_current_user), # Replaced with new WS auth dependency
    authenticated_user: Optional[DBUser] = Depends(get_current_user_from_ws_token),
    cm: CameraManager = Depends(get_camera_manager_dependency) 
):
    await websocket.accept()

    if not authenticated_user:
        print(f"[WebSocket Stream {camera_id}] Authentication failed. Closing connection.")
        await websocket.send_text("Error: Authentication failed or token missing.")
        await websocket.close(code=4001) # Custom WebSocket close code for auth failure
        return
    
    # If authenticated, you can use authenticated_user.username, etc.
    print(f"User '{authenticated_user.username}' authenticated for WebSocket stream on camera {camera_id}.")
    
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

# --- Serve Frontend Static Files ---

# Get the directory where main.py is located (i.e., CamCord/v1/app)
current_script_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the path to the frontend directory (CamCord/v1/frontend)
FRONTEND_DIR = os.path.join(current_script_dir, "..", "frontend")

# Check if the calculated FRONTEND_DIR actually exists
if not os.path.exists(FRONTEND_DIR) or not os.path.isdir(FRONTEND_DIR):
    print(f"!!! WARNING !!!")
    print(f"Frontend directory not found at the calculated path: {FRONTEND_DIR}")
    print(f"Current script directory (__file__): {__file__}")
    print(f"Please ensure the 'frontend' folder is located at CamCord/v1/frontend")
    # Optionally, raise an error or exit if frontend is critical
    # raise RuntimeError(f"Frontend directory not found: {FRONTEND_DIR}")
else:
    print(f"Attempting to serve static files from: {FRONTEND_DIR}")
    try:
        app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static-frontend-root")
        print(f"Frontend successfully mounted at '/'. Access at http://localhost:8000/")
    except Exception as e:
        print(f"!!! ERROR mounting static files: {e} !!!")
        print(f"Please check the directory path and permissions for {FRONTEND_DIR}")