# CamCord/v1/tests/test_api_admin_cameras.py
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.database import Camera as DBCamera, CameraSettings as DBCameraSettings
from app.schemas import CameraCreate, CameraUpdate, CameraResponse
from .helpers import create_test_user, get_auth_headers_for_user, seed_camera_with_settings
from app.main import camera_manager_global # For checking reloads

def test_create_camera_admin_success(test_client_fixture: TestClient, db_session_fixture: Session):
    admin_headers = get_auth_headers_for_user(test_client_fixture, "admin_crud_create", db_session_fixture=db_session_fixture, is_admin=True)
    camera_payload = {"name": "New Cam 1", "rtsp_url": "rtsp://newcam1", "is_active": True, "location": "Office"}

    response = test_client_fixture.post("/api/admin/cameras/", headers=admin_headers, json=camera_payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["name"] == "New Cam 1"
    assert data["rtsp_url"] == "rtsp://newcam1"

    db_cam = db_session_fixture.query(DBCamera).filter(DBCamera.id == data["id"]).first()
    assert db_cam is not None
    assert db_cam.settings is not None # Check settings were created
    # Check if CameraManager picked it up (requires reload to have happened)
    assert camera_manager_global.get_camera(data["id"]) is not None


def test_create_camera_non_admin_fails(test_client_fixture: TestClient, db_session_fixture: Session):
    user_headers = get_auth_headers_for_user(test_client_fixture, "user_crud_create", db_session_fixture=db_session_fixture, is_admin=False)
    camera_payload = {"name": "Forbidden Cam", "rtsp_url": "rtsp://forbidden"}
    response = test_client_fixture.post("/api/admin/cameras/", headers=user_headers, json=camera_payload)
    assert response.status_code == 403, response.text

def test_update_camera_admin_success(test_client_fixture: TestClient, db_session_fixture: Session):
    admin_headers = get_auth_headers_for_user(test_client_fixture, "admin_crud_update", db_session_fixture=db_session_fixture, is_admin=True)
    cam = seed_camera_with_settings(db_session_fixture, camera_id=101, name="CamToUpdate")
    camera_manager_global.reload_cameras_from_db() # Ensure CM knows this cam

    update_payload = {"name": "Updated Cam Name", "is_active": False}
    response = test_client_fixture.put(f"/api/admin/cameras/{cam.id}", headers=admin_headers, json=update_payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "Updated Cam Name"
    assert data["is_active"] == False
    # Check if CameraManager removed it (since is_active is now False)
    assert camera_manager_global.get_camera(cam.id) is None


def test_delete_camera_admin_success(test_client_fixture: TestClient, db_session_fixture: Session):
    admin_headers = get_auth_headers_for_user(test_client_fixture, "admin_crud_delete", db_session_fixture=db_session_fixture, is_admin=True)
    cam = seed_camera_with_settings(db_session_fixture, camera_id=102, name="CamToDelete")
    camera_manager_global.reload_cameras_from_db()

    cam_id_to_delete = cam.id
    response = test_client_fixture.delete(f"/api/admin/cameras/{cam_id_to_delete}", headers=admin_headers)
    assert response.status_code == 204, response.text

    assert db_session_fixture.query(DBCamera).filter(DBCamera.id == cam_id_to_delete).first() is None
    assert db_session_fixture.query(DBCameraSettings).filter(DBCameraSettings.camera_id == cam_id_to_delete).first() is None
    assert camera_manager_global.get_camera(cam_id_to_delete) is None
