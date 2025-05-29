import cv2
import time
import threading
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from .database import Camera as DBCamera, CameraSettings as DBCameraSettings # Assuming Camera and CameraSettings are the model names

class ManagedCamera:
    def __init__(self, db_camera: DBCamera, db_session: Session): # db_session to load settings
        self.db_camera = db_camera
        self.camera_id = db_camera.id
        self.name = db_camera.name
        self.rtsp_url = db_camera.rtsp_url 
        # TODO: Later, extend to support USB cameras using an index if rtsp_url is None

        self.video_capture = None
        self.lock = threading.Lock() # For thread-safe access to video_capture
        self.is_running = False
        self.settings: DBCameraSettings = None # To be loaded

        self._load_settings(db_session)
        self._connect()

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
        if self.rtsp_url:
            try:
                self.video_capture = cv2.VideoCapture(self.rtsp_url)
                if self.video_capture.isOpened():
                    self.is_running = True
                    print(f"[ManagedCamera {self.camera_id}] Connected to {self.rtsp_url}")
                else:
                    print(f"[ManagedCamera {self.camera_id}] Failed to open {self.rtsp_url}")
                    self.is_running = False
            except Exception as e:
                print(f"[ManagedCamera {self.camera_id}] Error connecting to {self.rtsp_url}: {e}")
                self.is_running = False
        # TODO: Handle USB camera connection (e.g., if self.camera_id is an int index)
        else:
            print(f"[ManagedCamera {self.camera_id}] No RTSP URL or device index configured.")
            self.is_running = False


    def get_frame(self):
        if not self.is_running or self.video_capture is None:
            return None
        with self.lock:
            ret, frame = self.video_capture.read()
        if not ret:
            # TODO: Handle reconnection logic if needed
            return None
        
        # TODO: Apply settings (resolution, brightness, night_vision etc.) from self.settings to the frame
        # Example for night vision (actual implementation might be more complex):
        # if self.settings and self.settings.night_vision:
        #     if len(frame.shape) == 3: # Color image
        #         frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        #         frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR) # Keep 3 channels for some overlays

        return frame

    def release(self):
        self.is_running = False
        with self.lock:
            if self.video_capture:
                self.video_capture.release()
                print(f"[ManagedCamera {self.camera_id}] Released.")
    
    def apply_settings_to_frame(self, frame):
        # Placeholder for applying brightness, contrast etc. from self.settings
        # This will be detailed in a subsequent step.
        if not self.settings or frame is None:
            return frame
        
        processed_frame = frame.copy()

        # Resolution: Typically set on VideoCapture, but can resize if needed post-capture
        # if self.settings.resolution:
        #     try:
        #         width, height = map(int, self.settings.resolution.split('x'))
        #         processed_frame = cv2.resize(processed_frame, (width, height))
        #     except ValueError:
        #         pass # Invalid resolution format

        # Night Vision (example, actual filter might be different)
        if self.settings.night_vision:
            if len(processed_frame.shape) == 3:
                gray = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2GRAY)
                # Simple thresholding for night vision effect, or could be a colormap
                # _, processed_frame_nv = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)
                # processed_frame = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR) # keep it 3 channel
                # A common way is to apply a bluish tint or use equalizeHist
                processed_frame = cv2.cvtColor(cv2.equalizeHist(gray), cv2.COLOR_GRAY2BGR)


        # Brightness & Contrast (OpenCV handles this via convertScaleAbs)
        # alpha for contrast (1.0-3.0), beta for brightness (0-100)
        # These are not direct 0-100 values for VideoCapture properties.
        # For post-processing:
        # contrast_factor = 1.0 + (self.settings.contrast - 50) / 50.0 
        # brightness_offset = self.settings.brightness - 50 
        # processed_frame = cv2.convertScaleAbs(processed_frame, alpha=contrast_factor, beta=brightness_offset)
        
        # Saturation: TODO (requires conversion to HSV and back)
        # Sharpness: TODO (requires kernel convolution)

        return processed_frame

class CameraManager:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.cameras: Dict[int, ManagedCamera] = {}
        self._load_cameras()

    def _load_cameras(self):
        active_cameras = self.db_session.query(DBCamera).filter(DBCamera.is_active == True).all()
        for db_cam in active_cameras:
            if db_cam.id not in self.cameras: # Avoid reloading if called multiple times
                self.cameras[db_cam.id] = ManagedCamera(db_camera=db_cam, db_session=self.db_session)
            else:
                # Potentially update existing ManagedCamera instance if needed
                pass 
        print(f"[CameraManager] Loaded {len(self.cameras)} active cameras.")

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
            frame = managed_cam.get_frame()
            if frame is not None:
                return managed_cam.apply_settings_to_frame(frame)
        return None
