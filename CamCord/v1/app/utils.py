import os
import cv2
import base64
import datetime
from pathlib import Path
from typing import Optional

LOG_DIR = Path("logs")
IMAGE_SAVE_DIR = Path("snapshots")
VIDEO_SAVE_DIR = Path("recordings")

# Ensure necessary directories exist
LOG_DIR.mkdir(parents=True, exist_ok=True)
IMAGE_SAVE_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_SAVE_DIR.mkdir(parents=True, exist_ok=True)

def log_event(event_type: str, message: str):
    """Logs events with timestamps."""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] [{event_type.upper()}] {message}\n"
    log_file = LOG_DIR / f"{datetime.date.today()}.log"
    with open(log_file, "a") as f:
        f.write(log_message)

def encode_frame(frame) -> str:
    """Converts a video frame to a base64-encoded JPEG string."""
    ret, buffer = cv2.imencode(".jpg", frame)
    if not ret:
        raise ValueError("Frame encoding failed.")
    jpg_as_text = base64.b64encode(buffer).decode("utf-8")
    return f"data:image/jpeg;base64,{jpg_as_text}"

def save_snapshot(camera_id: str, frame) -> str:
    """Saves a snapshot from a video frame and returns the file path."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{camera_id}_{timestamp}.jpg"
    file_path = IMAGE_SAVE_DIR / filename
    cv2.imwrite(str(file_path), frame)
    log_event("snapshot", f"Snapshot saved: {file_path}")
    return str(file_path)

def save_video_clip(camera_id: str, frames: list, fps: int = 20) -> str:
    """Saves a short video clip from frames and returns the file path."""
    if not frames:
        raise ValueError("No frames provided for video clip.")

    height, width, _ = frames[0].shape
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{camera_id}_{timestamp}.avi"
    file_path = VIDEO_SAVE_DIR / filename

    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(str(file_path), fourcc, fps, (width, height))

    for frame in frames:
        out.write(frame)

    out.release()
    log_event("video", f"Video clip saved: {file_path}")
    return str(file_path)

def get_system_uptime() -> str:
    """Returns the system uptime in a human-readable format."""
    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.readline().split()[0])
            uptime = str(datetime.timedelta(seconds=int(uptime_seconds)))
            return uptime
    except Exception as e:
        log_event("error", f"Failed to read uptime: {e}")
        return "Unknown"

def sanitize_filename(name: str) -> str:
    """Sanitizes filenames to prevent directory traversal or invalid characters."""
    return "".join(c for c in name if c.isalnum() or c in ("_", "-"))

def get_timestamp() -> str:
    """Returns a formatted timestamp string."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def check_camera_access(index: int = 0) -> bool:
    """Checks if the camera at the given index is accessible."""
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        return False
    cap.release()
    return True