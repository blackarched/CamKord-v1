# database.py

import os
import bcrypt
import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Default database path (can be overridden via env)
DB_PATH = os.getenv("CAMERA_SUITE_DB", "data/camera_suite.db")

# Ensure the data directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Initialize SQLAlchemy
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, connect_args={"check_same_thread": False})
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

# ----------------------------
# Database Models
# ----------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow) # Added

    logs = relationship("EventLog", back_populates="user") # Added relationship

    def verify_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode(), self.password_hash.encode())

    @staticmethod
    def hash_password(password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()

class EventLog(Base):
    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    # camera_id changed to ForeignKey to cameras.id
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Added user_id
    event_type = Column(String(50), nullable=False)
    event_description = Column(Text, nullable=True) # Renamed message to event_description

    # Relationships for EventLog
    user = relationship("User", back_populates="logs")
    camera = relationship("Camera", back_populates="logs")

# New Camera Model (inserted before CameraSettings as EventLog and CameraSettings refer to it)
class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    location = Column(String(100), nullable=True)
    rtsp_url = Column(String(255), nullable=True) # As per instruction, was nullable=False in models.py
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships for Camera
    logs = relationship("EventLog", back_populates="camera", cascade="all, delete-orphan")
    settings = relationship("CameraSettings", back_populates="camera", uselist=False, cascade="all, delete-orphan")


class CameraSettings(Base):
    __tablename__ = "camera_settings"

    id = Column(Integer, primary_key=True)
    # camera_id changed to ForeignKey to cameras.id
    camera_id = Column(Integer, ForeignKey("cameras.id"), unique=True, nullable=False)
    name = Column(String(100)) # Name might be redundant if Camera model has a name
    resolution = Column(String(32))   # Format: "1280x720"
    night_vision = Column(Boolean, default=False)
    autofocus = Column(Boolean, default=True)
    brightness = Column(Integer, default=50)
    contrast = Column(Integer, default=50)
    saturation = Column(Integer, default=50)
    sharpness = Column(Integer, default=50)
    microphone_enabled = Column(Boolean, default=True)

    # Motion detection settings
    motion_detection_enabled = Column(Boolean, default=False)
    motion_sensitivity = Column(Integer, default=30) # 0-100, 100=most sensitive
    record_on_motion = Column(Boolean, default=False)
    motion_min_area = Column(Integer, default=500) # Min contour area

    # Object detection settings
    object_detection_enabled = Column(Boolean, default=False)

    # Relationship for CameraSettings
    camera = relationship("Camera", back_populates="settings")

# ----------------------------
# Initialization Logic
# ----------------------------

def init_db():
    Base.metadata.create_all(engine)

    # Create default admin user if it doesn't exist
    session = SessionLocal()
    try:
        if not session.query(User).filter_by(username="admin").first():
            admin_password = os.getenv("CAMERA_SUITE_ADMIN_PASS")
            if not admin_password:
                print("[INIT] WARNING: CAMERA_SUITE_ADMIN_PASS environment variable not set. Default admin user 'admin' will NOT be created.")
            else:
                hashed_pw = User.hash_password(admin_password)
                admin_user = User(username="admin", password_hash=hashed_pw, is_admin=True)
                session.add(admin_user)
                session.commit()
                print("[INIT] Default admin user 'admin' created successfully using password from CAMERA_SUITE_ADMIN_PASS.")
        else:
            print("[INIT] Admin user 'admin' already exists.")
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}")
    finally:
        session.close()

# ----------------------------
# Utility: Log Events
# ----------------------------

def log_event(event_type: str, message: str, camera_id: str = None):
    session = SessionLocal()
    try:
        log = EventLog(event_type=event_type, message=message, camera_id=camera_id)
        session.add(log)
        session.commit()
    except Exception as e:
        print(f"[ERROR] Failed to log event: {e}")
    finally:
        session.close()