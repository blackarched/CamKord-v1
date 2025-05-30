import cv2
import os
import time
import threading
import numpy as np
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime # Added import
from .database import Camera as DBCamera, CameraSettings as DBCameraSettings, EventLog
from .config import settings as global_settings
from .object_detector import ObjectDetector # Added import

class ManagedCamera:
    def __init__(self, db_camera: DBCamera, db_session: Session, manager: 'CameraManager'): # Added manager
        self.db_camera = db_camera
        self.camera_id = db_camera.id
        self.name = db_camera.name
        self.manager = manager # Store manager reference
        self.rtsp_url = db_camera.rtsp_url
        # TODO: Later, extend to support USB cameras using an index if rtsp_url is None

        self.video_capture = None
        self.lock = threading.Lock() # For thread-safe access to video_capture
        self.is_running = False
        self.settings: DBCameraSettings = None # To be loaded

        # Recording attributes
        self.is_recording: bool = False
        self.video_writer: Optional[cv2.VideoWriter] = None
        self.recording_thread: Optional[threading.Thread] = None
        self.recording_dir: str = global_settings.RECORDING_DIR
        self.recording_fps: int = 20 # Default FPS for recording

        # Motion detection attributes
        self.motion_last_processed_gray_frame: Optional[np.ndarray] = None
        self.motion_debounce_seconds: float = 5.0
        self.last_motion_event_time: float = 0.0

        # Reconnection and monitoring attributes
        self.reconnect_attempts: int = 0
        self.max_reconnect_attempts: int = 5
        self.reconnect_delay_base: float = 2.0
        self.max_reconnect_delay: float = 60.0
        self.current_reconnect_delay: float = self.reconnect_delay_base
        self.last_successful_frame_time: Optional[float] = None
        self.consecutive_frame_read_failures: int = 0
        self.max_consecutive_frame_read_failures: int = 150

        self._load_settings(db_session)
        self._connect() # Initial connection attempt
        # No need to call _apply_initial_capture_properties here, _connect will do it on success

    def _handle_motion_event(self):
        current_time = time.time()
        if (current_time - self.last_motion_event_time) < self.motion_debounce_seconds:
            # Still in debounce period from last event
            return

        self.last_motion_event_time = current_time
        # print(f"[ManagedCamera {self.camera_id}] Motion Event Triggered at {time.ctime(current_time)}") # Replaced by DB log

        self.manager.record_camera_event(
            camera_id=self.camera_id,
            event_type="motion_detected",
            description=f"Motion detected on camera '{self.name}' (ID: {self.camera_id})"
        )

        if self.settings and self.settings.record_on_motion and not self.is_recording:
            print(f"[ManagedCamera {self.camera_id}] Record on motion is enabled. Starting recording.")
            if self.start_recording():
                print(f"[ManagedCamera {self.camera_id}] Recording started due to motion.")
            else:
                print(f"[ManagedCamera {self.camera_id}] Failed to start recording on motion (possibly already recording or camera issue).")

    def _detect_motion(self, frame_for_motion_detection: np.ndarray) -> bool:
        if not self.settings or not self.settings.motion_detection_enabled:
            return False

        gray = cv2.cvtColor(frame_for_motion_detection, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.motion_last_processed_gray_frame is None:
            self.motion_last_processed_gray_frame = gray
            return False

        # Sensitivity mapping for diff_thresh_val
        # Lower threshold means more sensitive. Map sensitivity 100 (most sensitive) to 5, 0 (least sensitive) to 50.
        diff_thresh_val = max(5, 50 - int(self.settings.motion_sensitivity * 0.45))

        frame_delta = cv2.absdiff(self.motion_last_processed_gray_frame, gray)
        thresh = cv2.threshold(frame_delta, diff_thresh_val, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)

        cnts, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        motion_found = False
        min_area = self.settings.motion_min_area if self.settings.motion_min_area else 500 # Default if not set
        for c in cnts:
            if cv2.contourArea(c) > min_area:
                motion_found = True
                break

        self.motion_last_processed_gray_frame = gray
        return motion_found

    def start_recording(self) -> bool:
        if self.is_recording:
            print(f"[ManagedCamera {self.camera_id}] Already recording.")
            return False
        if not self.is_running or not self.video_capture or not self.video_capture.isOpened():
            print(f"[ManagedCamera {self.camera_id}] Cannot start recording, camera not running/connected.")
            return False

        os.makedirs(self.recording_dir, exist_ok=True)
        filename = f"rec_cam{self.camera_id}_{int(time.time())}.mp4"
        filepath = os.path.join(self.recording_dir, filename)

        current_frame_raw = self.get_frame()
        if current_frame_raw is None:
            print(f"[ManagedCamera {self.camera_id}] Cannot get frame to determine recording dimensions.")
            return False
        current_frame_processed = self.apply_settings_to_frame(current_frame_raw)
        if current_frame_processed is None:
             print(f"[ManagedCamera {self.camera_id}] Cannot get processed frame for dimensions.")
             return False

        height, width, _ = current_frame_processed.shape

        actual_recording_fps = (self.settings.frame_rate
                               if hasattr(self.settings, 'frame_rate') and self.settings.frame_rate
                               else self.recording_fps)

        try:
            self.video_writer = cv2.VideoWriter(
                filepath,
                cv2.VideoWriter_fourcc(*'mp4v'),
                float(actual_recording_fps),
                (width, height)
            )
            if not self.video_writer.isOpened():
                print(f"[ManagedCamera {self.camera_id}] Failed to open VideoWriter for {filepath}")
                self.video_writer = None
                return False
        except Exception as e:
            print(f"[ManagedCamera {self.camera_id}] Exception opening VideoWriter: {e}")
            self.video_writer = None
            return False

        self.is_recording = True
        self.recording_thread = threading.Thread(target=self._record_loop, daemon=True)
        self.recording_thread.start()
        print(f"[ManagedCamera {self.camera_id}] Started recording to {filepath} at {actual_recording_fps} FPS.")
        return True

    def _record_loop(self):
        print(f"[ManagedCamera {self.camera_id}] Recording loop started.")
        actual_recording_fps = (self.settings.frame_rate
                               if hasattr(self.settings, 'frame_rate') and self.settings.frame_rate
                               else self.recording_fps)
        sleep_interval = 1.0 / actual_recording_fps

        while self.is_recording:
            if not self.video_writer or not self.video_writer.isOpened():
                print(f"[ManagedCamera {self.camera_id}] VideoWriter became unavailable. Stopping recording loop.")
                self.is_recording = False
                break

            frame_raw = self.get_frame()
            if frame_raw is not None:
                frame_to_record = self.apply_settings_to_frame(frame_raw)
                if frame_to_record is not None:
                    self.video_writer.write(frame_to_record)

            time.sleep(sleep_interval)

        if self.video_writer:
            print(f"[ManagedCamera {self.camera_id}] Releasing VideoWriter.")
            self.video_writer.release()
            self.video_writer = None
        print(f"[ManagedCamera {self.camera_id}] Recording loop stopped.")

    def stop_recording(self) -> bool:
        if not self.is_recording:
            print(f"[ManagedCamera {self.camera_id}] Not recording.")
            return False

        print(f"[ManagedCamera {self.camera_id}] Attempting to stop recording...")
        self.is_recording = False

        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=5.0)
            if self.recording_thread.is_alive():
                print(f"[ManagedCamera {self.camera_id}] Warning: Recording thread did not terminate in time.")

        if self.video_writer and self.video_writer.isOpened():
            print(f"[ManagedCamera {self.camera_id}] Forcibly releasing VideoWriter post-join.")
            self.video_writer.release()
        self.video_writer = None
        self.recording_thread = None
        print(f"[ManagedCamera {self.camera_id}] Recording stopped.")
        return True

    def reload_settings_and_apply(self, db_session: Session):
        print(f"[ManagedCamera {self.camera_id}] Reloading settings from DB.")
        # Ensure _load_settings can take a session and updates self.settings
        self._load_settings(db_session)
        if self.video_capture and self.video_capture.isOpened():
            # Ensure _apply_initial_capture_properties exists and applies settings
            self._apply_initial_capture_properties()
            print(f"[ManagedCamera {self.camera_id}] Re-applied initial capture properties.")
        elif self.is_running: # Check if it was supposed to be running
            print(f"[ManagedCamera {self.camera_id}] Camera was running but video_capture is not open. Attempting to reconnect.")
            self._connect() # Attempt to reconnect
            if self.video_capture and self.video_capture.isOpened():
                self._apply_initial_capture_properties()
                print(f"[ManagedCamera {self.camera_id}] Reconnected and re-applied initial capture properties.")
            else:
                 print(f"[ManagedCamera {self.camera_id}] Failed to reconnect. Capture properties not applied.")
        else:
            print(f"[ManagedCamera {self.camera_id}] Camera not running. Capture properties not applied.")

    def _apply_initial_capture_properties(self):
        if self.settings and self.video_capture and self.video_capture.isOpened():
            # Autofocus
            if hasattr(self.settings, 'autofocus') and self.settings.autofocus is not None:
                print(f"[ManagedCamera {self.camera_id}] Attempting to set autofocus to {self.settings.autofocus}")
                self.video_capture.set(cv2.CAP_PROP_AUTOFOCUS, 1 if self.settings.autofocus else 0)

            # Resolution (Attempt, may not work for all cameras post-connection)
            if hasattr(self.settings, 'resolution') and self.settings.resolution:
                try:
                    width, height = map(int, self.settings.resolution.split('x'))
                    print(f"[ManagedCamera {self.camera_id}] Attempting to set resolution to {width}x{height}")
                    self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, float(width))
                    self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, float(height))
                except ValueError:
                    print(f"[ManagedCamera {self.camera_id}] Invalid resolution format: {self.settings.resolution}")

            # Brightness (Attempt, camera-dependent, range 0-1 for some backends)
            if hasattr(self.settings, 'brightness') and self.settings.brightness is not None:
                 # Assuming settings.brightness is 0-100, map to 0.0-1.0 for CAP_PROP
                cap_brightness = self.settings.brightness / 100.0
                print(f"[ManagedCamera {self.camera_id}] Attempting to set CAP_PROP_BRIGHTNESS to {cap_brightness}")
                self.video_capture.set(cv2.CAP_PROP_BRIGHTNESS, cap_brightness)

            # Contrast (Attempt, camera-dependent, range 0-1 for some backends)
            if hasattr(self.settings, 'contrast') and self.settings.contrast is not None:
                cap_contrast = self.settings.contrast / 100.0
                print(f"[ManagedCamera {self.camera_id}] Attempting to set CAP_PROP_CONTRAST to {cap_contrast}")
                self.video_capture.set(cv2.CAP_PROP_CONTRAST, cap_contrast)

            # Saturation (Attempt, camera-dependent, range 0-1 for some backends)
            if hasattr(self.settings, 'saturation') and self.settings.saturation is not None:
                cap_saturation = self.settings.saturation / 100.0
                print(f"[ManagedCamera {self.camera_id}] Attempting to set CAP_PROP_SATURATION to {cap_saturation}")
                self.video_capture.set(cv2.CAP_PROP_SATURATION, cap_saturation)

    def _load_settings(self, db: Session):
        # Assuming a one-to-one relationship from Camera to CameraSettings
        # If settings is a backref on DBCamera, it might be self.db_camera.settings
        self.settings = db.query(DBCameraSettings).filter(DBCameraSettings.camera_id == self.camera_id).first()
        if not self.settings:
            # Create default settings if none exist? Or rely on them being created elsewhere?
            # For now, let's assume settings should exist.
            print(f"[ManagedCamera {self.camera_id}] WARNING: No settings found in DB.")
            # Or, create a default in-memory one:
            # self.settings = DBCameraSettings(camera_id=self.camera_id) # Fill with defaults

    def _connect(self):
        if not self.rtsp_url:
            print(f"[ManagedCamera {self.camera_id}] Configuration error: RTSP URL is not set. Camera will not connect.")
            self.is_running = False
            return False # Indicate connection failure

        print(f"[ManagedCamera {self.camera_id}] Attempting to connect to {self.rtsp_url}...")
        self.reconnect_attempts = 0 # Reset attempts for this connection cycle
        self.current_reconnect_delay = self.reconnect_delay_base

        while self.reconnect_attempts < self.max_reconnect_attempts:
            if self.video_capture: # Release existing if any (e.g. from a previous failed partial connect)
                with self.lock:
                    self.video_capture.release()
                self.video_capture = None

            try:
                with self.lock: # Protect VideoCapture creation
                    self.video_capture = cv2.VideoCapture(self.rtsp_url) # Add CAP_FFMPEG or other flags if needed

                if self.video_capture and self.video_capture.isOpened():
                    self.is_running = True
                    self.reconnect_attempts = 0 # Reset on success
                    self.consecutive_frame_read_failures = 0
                    self.last_successful_frame_time = time.time()
                    print(f"[ManagedCamera {self.camera_id}] Successfully connected to {self.rtsp_url}.")
                    # After successful (re)connection, apply properties
                    self._apply_initial_capture_properties()
                    return True # Indicate success
                else:
                    self.is_running = False # Ensure it's false if open fails
                    print(f"[ManagedCamera {self.camera_id}] Failed to open stream (attempt {self.reconnect_attempts + 1}/{self.max_reconnect_attempts}).")

            except Exception as e:
                self.is_running = False
                print(f"[ManagedCamera {self.camera_id}] Error connecting (attempt {self.reconnect_attempts + 1}/{self.max_reconnect_attempts}): {e}")

            self.reconnect_attempts += 1
            if self.reconnect_attempts < self.max_reconnect_attempts:
                print(f"[ManagedCamera {self.camera_id}] Retrying in {self.current_reconnect_delay:.1f} seconds...")
                time.sleep(self.current_reconnect_delay)
                # Exponential backoff for delay
                self.current_reconnect_delay = min(self.max_reconnect_delay, self.current_reconnect_delay * 2)
            else:
                print(f"[ManagedCamera {self.camera_id}] Max reconnect attempts reached for {self.rtsp_url}. Giving up for now.")
                break # Exit loop

        self.is_running = False # Explicitly set to false if loop finishes without success
        return False # Indicate connection failure


    def get_frame(self): # This is the raw frame getter
        if not self.is_running: # If not supposed to be running (e.g. after max retries in _connect)
            # Check if enough time has passed to try connecting again (e.g., after a longer pause)
            # This could be a periodic check by CameraManager too.
            # For now, if not is_running, it implies _connect failed definitively.
            return None

        if not self.video_capture or not self.video_capture.isOpened():
            print(f"[ManagedCamera {self.camera_id}] VideoCapture not open. Attempting to reconnect.")
            if self._connect(): # Try to reconnect
                # If _connect succeeds, it sets is_running and applies initial props.
                # Then try to get a frame again (but avoid recursion if _connect calls get_frame)
                # For now, let _connect handle the state, and next call to get_frame will try.
                print(f"[ManagedCamera {self.camera_id}] Reconnected. Frame will be fetched on next call.")
            else:
                print(f"[ManagedCamera {self.camera_id}] Reconnect failed in get_frame.")
                self.is_running = False # Ensure it's marked as down
            return None

        ret, frame = False, None
        try:
            with self.lock: # Protect read operation
                if self.video_capture and self.video_capture.isOpened(): # Double check inside lock
                     ret, frame = self.video_capture.read()
        except Exception as e:
            print(f"[ManagedCamera {self.camera_id}] Exception during video_capture.read(): {e}")
            ret = False # Treat as a read failure

        if not ret:
            self.consecutive_frame_read_failures += 1
            if self.consecutive_frame_read_failures >= self.max_consecutive_frame_read_failures:
                print(f"[ManagedCamera {self.camera_id}] Max consecutive frame read failures ({self.consecutive_frame_read_failures}). Stream lost. Releasing and attempting reconnect cycle.")
                self.is_running = False # Mark as not running before attempting _connect
                with self.lock: # Ensure capture is released before _connect tries to make a new one
                    if self.video_capture:
                        self.video_capture.release()
                    self.video_capture = None
                self._connect() # This will try to reconnect and set is_running if successful
            else:
                # Log less verbosely for intermittent failures
                if self.consecutive_frame_read_failures % 30 == 0: # Log every ~1 second if 30fps
                    print(f"[ManagedCamera {self.camera_id}] Frame read failed (consecutive: {self.consecutive_frame_read_failures}).")
            return None

        self.consecutive_frame_read_failures = 0
        self.last_successful_frame_time = time.time()
        return frame

    def release(self):
        print(f"[ManagedCamera {self.camera_id}] Releasing camera resources...")
        self.is_running = False # Signal any loops to stop
        if self.is_recording:
            self.stop_recording() # Ensure recording stops and thread joins

        with self.lock:
            if self.video_capture:
                self.video_capture.release()
                self.video_capture = None

        self.reconnect_attempts = 0 # Reset for next potential connect
        self.consecutive_frame_read_failures = 0
        print(f"[ManagedCamera {self.camera_id}] Released.")

    def apply_settings_to_frame(self, frame):
        if not self.settings or frame is None:
            return frame

        processed_frame = frame.copy()

        # Night Vision (Example from before, ensure it's robust)
        if self.settings.night_vision:
            if len(processed_frame.shape) == 3 and processed_frame.shape[2] == 3: # Check if it's a color image
                gray = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2GRAY)
                processed_frame = cv2.cvtColor(cv2.equalizeHist(gray), cv2.COLOR_GRAY2BGR)
            elif len(processed_frame.shape) == 2: # Already grayscale
                processed_frame = cv2.cvtColor(cv2.equalizeHist(processed_frame), cv2.COLOR_GRAY2BGR)


        # Brightness/Contrast (Post-processing if CAP_PROP didn't work or for fine-tuning)
        # These are applied relative to the current state of the frame.
        # Map settings (0-100) to factors/offsets. 50 is neutral.
        if hasattr(self.settings, 'brightness') and self.settings.brightness is not None and \
           hasattr(self.settings, 'contrast') and self.settings.contrast is not None:
            # alpha for contrast (e.g., 0.5 to 1.5), beta for brightness (e.g., -50 to 50)
            alpha = self.settings.contrast / 50.0  # contrast: 50->1.0 (normal), 100->2.0 (high), 0->0.0 (low)
            beta = (self.settings.brightness - 50) * 1 # brightness: 50->0 (normal), 100->+50 (high), 0->-50 (low)
            if alpha != 1.0 or beta != 0: # Apply only if changed from neutral
                 processed_frame = cv2.convertScaleAbs(processed_frame, alpha=alpha, beta=beta)

        # Saturation (Post-processing)
        if hasattr(self.settings, 'saturation') and self.settings.saturation is not None:
            if len(processed_frame.shape) == 3 and processed_frame.shape[2] == 3: # Must be color image
                saturation_factor = self.settings.saturation / 50.0 # 50->1.0, 100->2.0, 0->0.0
                if saturation_factor != 1.0: # Apply only if changed
                    hsv = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2HSV)
                    # Ensure hsv[:, :, 1] is float for multiplication, then clip and convert back to uint8
                    hsv_s_float = hsv[:, :, 1].astype(np.float32)
                    hsv_s_float = cv2.multiply(hsv_s_float, saturation_factor)
                    hsv[:, :, 1] = np.clip(hsv_s_float, 0, 255).astype(np.uint8)
                    processed_frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

        # Sharpness (Post-processing)
        if hasattr(self.settings, 'sharpness') and self.settings.sharpness is not None and self.settings.sharpness != 50: # 50 is neutral
            # Apply only if sharpness is greater than neutral (e.g. > 50 for sharpening)
            if self.settings.sharpness > 50:
                # A simple sharpening kernel. More complex kernels could be used.
                kernel = np.array([[-1, -1, -1],
                                   [-1,  9, -1],
                                   [-1, -1, -1]])
                # Adjust center based on sharpness intensity (simple example)
                # intensity_factor = (self.settings.sharpness - 50) / 50.0 # 0 to 1 for 50-100
                # kernel[1,1] = 9 + intensity_factor * 4 # e.g. center from 9 to 13
                processed_frame = cv2.filter2D(processed_frame, -1, kernel)
            # elif self.settings.sharpness < 50: # Blurring for sharpness < 50
            #    blur_intensity = ...
            #    processed_frame = cv2.GaussianBlur(processed_frame, (kernel_size, kernel_size), 0)

        # Object Detection (apply after all other visual processing)
        if self.settings and hasattr(self.settings, 'object_detection_enabled') and \
           self.settings.object_detection_enabled and \
           self.manager.object_detector and self.manager.object_detector.net is not None:
            try:
                # Make a copy to ensure original is not modified if not needed elsewhere,
                # or if detect method modifies frame in place and it's undesirable.
                frame_to_detect_on = processed_frame.copy()
                detections, frame_with_overlays = self.manager.object_detector.detect(frame_to_detect_on)

                # If detections occurred, you might want to log them or handle them.
                # For now, we just use the frame with overlays.
                # if detections:
                #    print(f"[ManagedCamera {self.camera_id}] Detected: {', '.join([d['label'] for d in detections])}")

                return frame_with_overlays # Return the frame with detection overlays
            except Exception as e:
                print(f"[ManagedCamera {self.camera_id}] Error during object detection: {e}")
                # Fall through to return the original processed_frame without detection overlays

        return processed_frame

class CameraManager:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.cameras: Dict[int, ManagedCamera] = {}
        self.object_detector = ObjectDetector() # Initialize ObjectDetector
        self._load_cameras() # Initial load

    def _load_cameras(self): # Current method in CameraManager
        print(f"[CameraManager] Clearing and reloading camera instances...")
        # Release any existing camera resources before clearing
        for cam_id_to_release in list(self.cameras.keys()): # Iterate over a copy of keys
            managed_cam_to_release = self.cameras.pop(cam_id_to_release)
            managed_cam_to_release.release()
        # self.cameras dictionary is now empty.

        # Ensure db_session is valid and active
        if not self.db_session or self.db_session.is_active == False:
            # This case should ideally not happen if db_session is managed well.
            # If it's possible, re-acquire a session or log error.
            # For tests, db_session is patched. For runtime, it's from main.py.
            print("[CameraManager] Warning: db_session is not active. Cannot load cameras.")
            return

        active_cameras_from_db = self.db_session.query(DBCamera).filter(DBCamera.is_active == True).all()
        for db_cam_from_db in active_cameras_from_db:
            self.cameras[db_cam_from_db.id] = ManagedCamera(
                db_camera=db_cam_from_db,
                db_session=self.db_session, # Pass the manager's session for ManagedCamera's initial settings load
                manager=self
            )
        print(f"[CameraManager] Loaded/Refreshed {len(self.cameras)} active cameras.")

    def reload_cameras_from_db(self):
        print("[CameraManager] Publicly requested: Reloading all cameras from database...")
        self._load_cameras() # Call the modified _load_cameras

    def record_camera_event(self, camera_id: int, event_type: str, description: str):
        # This method uses the CameraManager's own db_session.
        # This session is managed alongside CameraManager's lifecycle.
        try:
            # Make sure self.db_session is the active SQLAlchemy session for CameraManager
            new_event = EventLog(
                camera_id=camera_id,
                event_type=event_type,
                event_description=description,
                timestamp=datetime.utcnow()
            )
            self.db_session.add(new_event)
            self.db_session.commit()
            # print(f"[CameraManager] Logged event: CamID {camera_id}, Type: {event_type}, Desc: {description}")
        except Exception as e:
            self.db_session.rollback() # Rollback on error
            print(f"[CameraManager] Error logging event for cam {camera_id} to DB: {e}")

    def get_camera(self, camera_id: int) -> Optional[ManagedCamera]:
        return self.cameras.get(camera_id)

    def get_all_cameras(self) -> List[ManagedCamera]:
        return list(self.cameras.values())

    def shutdown(self):
        print("[CameraManager] Shutting down...")
        for cam_id in list(self.cameras.keys()): # Iterate over keys for safe removal
            managed_cam = self.cameras.pop(cam_id)
            managed_cam.release()
        print("[CameraManager] All cameras released.")

    def get_frame_from_camera(self, camera_id: int):
        managed_cam = self.get_camera(camera_id)
        if managed_cam and managed_cam.is_running:
            raw_frame = managed_cam.get_frame() # Get the raw frame
            if raw_frame is not None:
                # Apply visual settings first
                processed_frame = managed_cam.apply_settings_to_frame(raw_frame)

                # Then, if motion detection is enabled, detect motion on the processed frame
                if processed_frame is not None and managed_cam.settings and \
                   managed_cam.settings.motion_detection_enabled:
                    # Pass a copy for motion detection if _detect_motion might modify it (it doesn't currently)
                    if managed_cam._detect_motion(processed_frame.copy()):
                        managed_cam._handle_motion_event() # Has debounce logic

                return processed_frame # Return the visually processed frame
        return None

    def notify_settings_updated(self, camera_id: int, db_session_for_reload: Session):
        managed_cam = self.get_camera(camera_id)
        if managed_cam:
            print(f"[CameraManager] Notifying camera {camera_id} of settings update.")
            # Pass the db_session_for_reload for the ManagedCamera to use for its own query
            managed_cam.reload_settings_and_apply(db_session_for_reload)
        else:
            print(f"[CameraManager] Cannot notify settings update, camera {camera_id} not found or not active.")