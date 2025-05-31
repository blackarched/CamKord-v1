# CamCord/v1/tests/helpers.py
import os
from sqlalchemy.orm import Session
from app.database import User as DBUser, Camera as DBCamera, CameraSettings as DBCameraSettings

def create_test_user(db: Session, username: str, password_override=None, is_admin=False) -> tuple[DBUser, str]:
    password = password_override or os.getenv("CAMERA_SUITE_ADMIN_PASS", "testpassword123")
    user = db.query(DBUser).filter(DBUser.username == username).first()
    if not user:
        hashed_pw = DBUser.hash_password(password) # Assuming static method on DBUser
        user = DBUser(username=username, password_hash=hashed_pw, is_admin=is_admin)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user, password

def get_auth_headers_for_user(test_client, username: str, password_override=None, db_session_fixture=None, is_admin=False) -> dict:
    if db_session_fixture: # Ensure user exists if session provided
         _, password = create_test_user(db_session_fixture, username, password_override, is_admin)
    else: # Assume user exists or password_override is for a known user
        password = password_override or "testpassword123"

    login_response = test_client.post("/auth/token", data={"username": username, "password": password})
    assert login_response.status_code == 200, f"Login failed for {username}: {login_response.text}"
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def seed_camera_with_settings(db: Session, camera_id: int, name: str, is_active: bool = True, user_id=None) -> DBCamera:
    cam = db.query(DBCamera).filter(DBCamera.id == camera_id).first()
    if not cam:
        cam = DBCamera(id=camera_id, name=name, rtsp_url=f"rtsp://cam{camera_id}", is_active=is_active)
        db.add(cam)
        db.commit()

    settings = db.query(DBCameraSettings).filter(DBCameraSettings.camera_id == cam.id).first()
    if not settings:
        settings = DBCameraSettings(camera_id=cam.id, resolution="640x480", brightness=50) # Basic defaults
        db.add(settings)
        db.commit()
    db.refresh(cam)
    return cam
