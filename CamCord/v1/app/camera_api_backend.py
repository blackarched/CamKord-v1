from fastapi import FastAPI, UploadFile, File, HTTPException from fastapi.middleware.cors import CORSMiddleware from fastapi.responses import StreamingResponse, JSONResponse from pydantic import BaseModel import cv2 import threading import io import time import os import logging

app = FastAPI()

app.add_middleware( CORSMiddleware, allow_origins=[""], allow_credentials=True, allow_methods=[""], allow_headers=["*"], )

camera = cv2.VideoCapture(0)

if not camera.isOpened(): raise RuntimeError("Camera failed to initialize")

is_recording = False night_vision = False autofocus = True recording_thread = None video_writer = None

log_file_path = "logs/events.log" os.makedirs(os.path.dirname(log_file_path), exist_ok=True) logging.basicConfig(filename=log_file_path, level=logging.INFO)

def log_event(message): timestamp = time.strftime("%Y-%m-%d %H:%M:%S") logging.info(f"[{timestamp}] {message}")

def apply_night_vision(frame): return cv2.applyColorMap(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.COLORMAP_BONE)

def record(): global is_recording, video_writer fourcc = cv2.VideoWriter_fourcc(*'XVID') filename = f"recordings/recording_{int(time.time())}.avi" os.makedirs("recordings", exist_ok=True) video_writer = cv2.VideoWriter(filename, fourcc, 20.0, (640, 480)) log_event("Recording started") while is_recording: ret, frame = camera.read() if ret: if night_vision: frame = apply_night_vision(frame) video_writer.write(frame) video_writer.release() log_event("Recording stopped")

@app.get("/video") def stream_video(): def generate(): while True: ret, frame = camera.read() if not ret: break if night_vision: frame = apply_night_vision(frame) _, jpeg = cv2.imencode('.jpg', frame) frame_bytes = jpeg.tobytes() yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

return StreamingResponse(generate(), media_type='multipart/x-mixed-replace; boundary=frame')

@app.post("/snapshot") def take_snapshot(): ret, frame = camera.read() if not ret: raise HTTPException(status_code=500, detail="Failed to read from camera") if night_vision: frame = apply_night_vision(frame) filename = f"snapshots/snapshot_{int(time.time())}.jpg" os.makedirs("snapshots", exist_ok=True) cv2.imwrite(filename, frame) log_event("Snapshot taken") return {"message": "Snapshot saved", "filename": filename}

@app.post("/recording/start") def start_recording(): global is_recording, recording_thread if not is_recording: is_recording = True recording_thread = threading.Thread(target=record) recording_thread.start() return {"message": "Recording started"} return {"message": "Recording already in progress"}

@app.post("/recording/stop") def stop_recording(): global is_recording if is_recording: is_recording = False recording_thread.join() return {"message": "Recording stopped"} return {"message": "No recording in progress"}

class ToggleRequest(BaseModel): enabled: bool

@app.post("/toggle/night_vision") def toggle_night_vision(data: ToggleRequest): global night_vision night_vision = data.enabled log_event(f"Night vision {'enabled' if night_vision else 'disabled'}") return {"night_vision": night_vision}

@app.post("/toggle/autofocus") def toggle_autofocus(data: ToggleRequest): global autofocus autofocus = data.enabled log_event(f"Autofocus {'enabled' if autofocus else 'disabled'}") return {"autofocus": autofocus}

@app.get("/logs") def get_logs(): try: with open(log_file_path, "r") as log_file: logs = log_file.readlines() return JSONResponse(content={"logs": logs}) except Exception as e: raise HTTPException(status_code=500, detail=str(e))
