from fastapi import FastAPI, Response, Request from fastapi.responses import StreamingResponse, FileResponse, JSONResponse from fastapi.middleware.cors import CORSMiddleware import cv2 import threading import time import io from PIL import Image import numpy as np import os import datetime

app = FastAPI()

app.add_middleware( CORSMiddleware, allow_origins=[""], allow_credentials=True, allow_methods=[""], allow_headers=["*"], )

Global camera and settings

camera = cv2.VideoCapture(0) if not camera.isOpened(): raise RuntimeError("Could not start camera.")

camera_lock = threading.Lock() motion_detected = False recording = False motion_sensitivity = 50000  # pixel difference threshold recording_thread = None video_writer = None recording_dir = "recordings" os.makedirs(recording_dir, exist_ok=True)

State settings

settings = { "night_vision": False, "zoom": 1.0, "motion_detected": False }

Motion detection state

last_frame = None motion_lock = threading.Lock()

def apply_night_vision(frame): gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) enhanced = cv2.equalizeHist(gray) return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)

def apply_zoom(frame, zoom_factor): if zoom_factor == 1.0: return frame h, w = frame.shape[:2] center_x, center_y = w // 2, h // 2 radius_x, radius_y = int(w / (2 * zoom_factor)), int(h / (2 * zoom_factor)) min_x, max_x = center_x - radius_x, center_x + radius_x min_y, max_y = center_y - radius_y, center_y + radius_y cropped = frame[min_y:max_y, min_x:max_x] return cv2.resize(cropped, (w, h))

def detect_motion(current_frame): global last_frame gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY) gray = cv2.GaussianBlur(gray, (21, 21), 0)

if last_frame is None:
    last_frame = gray
    return False

frame_delta = cv2.absdiff(last_frame, gray)
thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
thresh = cv2.dilate(thresh, None, iterations=2)
cnts, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

motion_area = sum(cv2.contourArea(c) for c in cnts)
last_frame = gray
return motion_area > motion_sensitivity

def record_video(): global recording, video_writer fourcc = cv2.VideoWriter_fourcc(*'mp4v') now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") output_path = os.path.join(recording_dir, f"motion_{now}.mp4") fps = 20.0 width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH)) height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT)) video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height)) start_time = time.time() while recording: with camera_lock: ret, frame = camera.read() if not ret: break if settings["night_vision"]: frame = apply_night_vision(frame) frame = apply_zoom(frame, settings["zoom"]) video_writer.write(frame) time.sleep(1 / fps) video_writer.release()

def generate_frames(): global motion_detected, recording, recording_thread while True: with camera_lock: success, frame = camera.read() if not success: continue

if settings["night_vision"]:
        frame = apply_night_vision(frame)

    frame = apply_zoom(frame, settings["zoom"])

    if detect_motion(frame):
        motion_detected = True
        settings["motion_detected"] = True
        if not recording:
            recording = True
            recording_thread = threading.Thread(target=record_video)
            recording_thread.start()
    else:
        settings["motion_detected"] = False

    _, buffer = cv2.imencode('.jpg', frame)
    frame_bytes = buffer.tobytes()
    yield (b'--frame\r\n'
           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.get("/video_feed") def video_feed(): return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/snapshot") def snapshot(): with camera_lock: ret, frame = camera.read() if not ret: return Response(status_code=500)

if settings["night_vision"]:
    frame = apply_night_vision(frame)
frame = apply_zoom(frame, settings["zoom"])

_, buffer = cv2.imencode('.jpg', frame)
return Response(content=buffer.tobytes(), media_type="image/jpeg")

@app.post("/toggle_night_vision") def toggle_night_vision(): settings["night_vision"] = not settings["night_vision"] return {"night_vision": settings["night_vision"]}

@app.post("/set_zoom/{level}") def set_zoom(level: float): if 1.0 <= level <= 4.0: settings["zoom"] = level return {"zoom": level} else: return JSONResponse(status_code=400, content={"error": "Zoom level must be between 1.0 and 4.0"})

@app.get("/status") def get_status(): return settings
