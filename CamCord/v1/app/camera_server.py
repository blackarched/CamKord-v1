camera_server.py

import cv2 import threading import time import os from fastapi import FastAPI, WebSocket, WebSocketDisconnect from fastapi.middleware.cors import CORSMiddleware from fastapi.responses import StreamingResponse from starlette.staticfiles import StaticFiles from starlette.requests import Request import numpy as np import uvicorn

app = FastAPI()

app.add_middleware( CORSMiddleware, allow_origins=[""], allow_credentials=True, allow_methods=[""], allow_headers=["*"], )

Mount static frontend assets if available

app.mount("/static", StaticFiles(directory="static"), name="static")

class CameraHandler: def init(self, index=0): self.index = index self.capture = cv2.VideoCapture(index) self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280) self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720) self.frame = None self.running = True self.night_vision = False self.zoom_level = 1.0 self.lock = threading.Lock() threading.Thread(target=self._update_frame, daemon=True).start()

def _update_frame(self):
    while self.running:
        ret, frame = self.capture.read()
        if ret:
            with self.lock:
                frame = self.apply_zoom(frame)
                if self.night_vision:
                    frame = self.apply_night_vision(frame)
                self.frame = frame
        time.sleep(0.01)

def apply_night_vision(self, frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    eq = cv2.equalizeHist(gray)
    return cv2.cvtColor(eq, cv2.COLOR_GRAY2BGR)

def apply_zoom(self, frame):
    if self.zoom_level == 1.0:
        return frame
    h, w = frame.shape[:2]
    center_x, center_y = w // 2, h // 2
    new_w, new_h = int(w / self.zoom_level), int(h / self.zoom_level)
    x1, y1 = center_x - new_w // 2, center_y - new_h // 2
    x2, y2 = x1 + new_w, y1 + new_h
    cropped = frame[y1:y2, x1:x2]
    return cv2.resize(cropped, (w, h))

def get_frame(self):
    with self.lock:
        return self.frame.copy() if self.frame is not None else None

def toggle_night_vision(self):
    self.night_vision = not self.night_vision

def set_zoom_level(self, level):
    try:
        level = float(level)
        if 1.0 <= level <= 4.0:
            self.zoom_level = level
    except ValueError:
        pass

def stop(self):
    self.running = False
    self.capture.release()

camera_handler = CameraHandler()

@app.get("/video_feed") def video_feed(): def generate(): while True: frame = camera_handler.get_frame() if frame is not None: _, buffer = cv2.imencode('.jpg', frame) yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n') time.sleep(0.03) return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.post("/toggle_night_vision") def toggle_night(): camera_handler.toggle_night_vision() return {"night_vision": camera_handler.night_vision}

@app.post("/set_zoom/{level}") def set_zoom(level: str): camera_handler.set_zoom_level(level) return {"zoom": camera_handler.zoom_level}

@app.get("/snapshot") def snapshot(): frame = camera_handler.get_frame() if frame is not None: timestamp = time.strftime("%Y-%m-%d_%H-%M-%S") filename = f"snapshot_{timestamp}.jpg" path = os.path.join("snapshots", filename) os.makedirs("snapshots", exist_ok=True) cv2.imwrite(path, frame) return {"saved_to": path} return {"error": "No frame available"}

if name == "main": uvicorn.run("camera_server:app", host="0.0.0.0", port=8000, reload=False)
