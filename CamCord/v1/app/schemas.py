from pydantic import BaseModel, EmailStr, Field, conint
from typing import Optional, List
from datetime import datetime


# ========== AUTHENTICATION SCHEMAS ==========

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[int] = None # Retained as per instruction (although user_auth_backend.py uses username in TokenData)

class UserLogin(BaseModel): # Modified
    username: str # Changed from email
    password: str


# ========== USER SCHEMAS ==========

class UserBase(BaseModel): # Modified
    username: str
    email: Optional[EmailStr] = None

class UserCreate(UserBase): # Modified (password already there, ensuring it aligns)
    password: str

class UserResponse(UserBase): # Modified
    id: int
    is_admin: bool = False
    created_at: datetime

    class Config:
        orm_mode = True

# New CameraInfo schema for list_cameras endpoint
class CameraInfo(BaseModel):
    id: int
    name: str
    rtsp_url: Optional[str] = None
    is_running: bool
    motion_detection_enabled: Optional[bool] = None
    object_detection_enabled: Optional[bool] = None

    class Config:
        orm_mode = True # If you might populate from an ORM object directly later


# ========== CAMERA SCHEMAS ==========

class CameraBase(BaseModel): # Modified
    name: str = Field(..., max_length=100)
    location: Optional[str] = None
    rtsp_url: Optional[str] = None # Made Optional
    is_active: bool = True

class CameraCreate(CameraBase): # Unchanged, inherits from modified CameraBase
    pass

class CameraUpdate(BaseModel): # Modified
    name: Optional[str] = None
    location: Optional[str] = None
    rtsp_url: Optional[str] = None
    is_active: Optional[bool] = None

class CameraResponse(CameraBase): # Modified
    id: int
    created_at: datetime
    # status and last_checked removed

    class Config:
        orm_mode = True


# ========== CAMERA SETTINGS ==========

# Replaced existing CameraSettings with new structure
class CameraSettingsBase(BaseModel):
    resolution: Optional[str] = "1280x720"
    night_vision: Optional[bool] = False
    autofocus: Optional[bool] = True
    brightness: Optional[int] = Field(default=50, ge=0, le=100)
    contrast: Optional[int] = Field(default=50, ge=0, le=100)
    saturation: Optional[int] = Field(default=50, ge=0, le=100)
    sharpness: Optional[int] = Field(default=50, ge=0, le=100)
    microphone_enabled: Optional[bool] = True

    # Motion detection settings
    motion_detection_enabled: Optional[bool] = False
    motion_sensitivity: Optional[int] = Field(default=30, ge=0, le=100)
    record_on_motion: Optional[bool] = False
    motion_min_area: Optional[int] = Field(default=500, ge=100, le=10000)

    # Object detection settings
    object_detection_enabled: Optional[bool] = False

class CameraSettingsCreate(CameraSettingsBase):
    # No camera_id here, assumes it's part of path or parent resource
    pass

class CameraSettingsUpdate(CameraSettingsBase): # All fields already optional in Base
    pass

class CameraSettingsResponse(CameraSettingsBase):
    id: int
    camera_id: int

    class Config:
        orm_mode = True


# ========== STREAM CONTROL ==========

class StreamControl(BaseModel): # Retained
    camera_id: int
    action: str  # "start", "stop", "snapshot", etc.


# ========== LOGS & ACTIVITY ==========

# Renamed EventLog to EventLogResponse and modified
class EventLogResponse(BaseModel):
    id: int
    timestamp: datetime
    event_type: str
    event_description: Optional[str] = None # Renamed from message, made optional
    user_id: Optional[int] = None
    camera_id: Optional[int] = None

    class Config:
        orm_mode = True

# New EventLogCreate schema
class EventLogCreate(BaseModel):
    event_type: str
    event_description: Optional[str] = None
    user_id: Optional[int] = None
    camera_id: Optional[int] = None


# ========== DASHBOARD SUMMARY ==========

class DashboardStatus(BaseModel):
    total_cameras: int
    active_streams: int
    errors_today: int
    last_event: Optional[str]