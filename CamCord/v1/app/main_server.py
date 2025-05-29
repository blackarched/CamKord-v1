import cv2
import uvicorn
import threading
import logging
from fastapi import FastAPI, Request, Response, Depends, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from typing import Generator, Optional
import secrets
import os

from camera_module import CameraManager
from security_utils import verify_user, get_password_hash, authenticate_user, create_access_token, get_current_user
from camera_controls import apply_night_vision_filter, apply_image_adjustments

# -------------------------------
# Logger Setup
# -------------------------------
logging.basicConfig(
    format='%(asctime)s %(levelname)s: %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("server.log"),
        logging.StreamHandler()
    ]
)

# -------------------------------
# App Initialization
# -------------------------------
app = FastAPI(title="Personal Security Camera Server")
camera_manager = CameraManager()
camera_index = 0  # Default camera index

# -------------------------------
# Middleware
# -------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Consider limiting this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# Auth Models
# -------------------------------
class LoginRequest(BaseModel):
    username: str
    password: str

# -------------------------------
# API Endpoints
# -------------------------------

@app.post("/login")
def login(request: LoginRequest):
    if authenticate_user(request.username, request.password):
        token = create_access_token(username=request.username)
        logging.info(f"User '{request.username}' logged in successfully.")
        return {"access_token": token}
    else:
        logging.warning(f"Failed login attempt for username: {request.username}")
        raise HTTPException(status_code=401, detail="Invalid username or password")

@app.get("/video_feed")
def video_feed(user: str = Depends(get_current_user)):
    """Stream live video feed from selected camera."""
    def generate() -> Generator[bytes, None, None]:
        while True:
            frame = camera_manager.get_frame(camera_index)
            if frame is None:
                continue
            if camera_manager.filters['night_vision']:
                frame = apply_night_vision_filter(frame)
            frame = apply_image_adjustments(frame)
            ret, jpeg = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

    logging.info("Video feed accessed.")
    return StreamingResponse(generate(), media_type='multipart/x-mixed-replace; boundary=frame')

@app.post("/snapshot")
def take_snapshot(user: str = Depends(get_current_user)):
    """Capture a snapshot from the live feed."""
    frame = camera_manager.get_frame(camera_index)
    if frame is None:
        raise HTTPException(status_code=500, detail="Unable to capture frame.")
    filename = f"snapshots/snapshot_{camera_index}_{secrets.token_hex(4)}.jpg"
    os.makedirs("snapshots", exist_ok=True)
    cv2.imwrite(filename, frame)
    logging.info(f"Snapshot saved to {filename}")
    return {"message": "Snapshot captured.", "file": filename}

@app.post("/controls/night_vision")
def toggle_night_vision(state: bool, user: str = Depends(get_current_user)):
    camera_manager.filters['night_vision'] = state
    logging.info(f"Night vision set to {state}")
    return {"message": f"Night vision set to {state}"}

@app.post("/controls/image_settings")
def set_image_settings(
    brightness: Optional[int] = None,
    contrast: Optional[int] = None,
    saturation: Optional[int] = None,
    user: str = Depends(get_current_user)
):
    if brightness is not None:
        camera_manager.settings['brightness'] = brightness
    if contrast is not None:
        camera_manager.settings['contrast'] = contrast
    if saturation is not None:
        camera_manager.settings['saturation'] = saturation
    logging.info(f"Image settings updated: {camera_manager.settings}")
    return {"message": "Image settings updated.", "settings": camera_manager.settings}

@app.post("/controls/autofocus")
def toggle_autofocus(state: bool, user: str = Depends(get_current_user)):
    result = camera_manager.toggle_autofocus(camera_index, state)
    return {"message": result}

@app.get("/status")
def get_status(user: str = Depends(get_current_user)):
    info = camera_manager.get_camera_info(camera_index)
    return {"camera_status": info}

# -------------------------------
# Entry Point
# -------------------------------
if __name__ == "__main__":
    logging.info("Starting Personal Security Camera Server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)