# CamCord/v1/tests/test_api_cameras.py
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import os # Added
import numpy as np # Added
from unittest import mock # Added

# Assuming conftest.py or pytest.ini handles pythonpath for app module
from database import Camera as DBCamera, User as DBUser, CameraSettings as DBCameraSettings
from schemas import CameraSettingsResponse
from app.config import settings as app_settings # Added for SNAPSHOT_DIR
from .test_api_auth import create_test_admin_user # Helper from auth tests

def seed_cameras(db: Session):
    # Clean up existing cameras to ensure predictable test state if session is reused somehow
    db.query(DBCamera).delete() 
    db.commit()

    cam1 = DBCamera(id=1, name="Test Cam 1", rtsp_url="rtsp://test1", is_active=True)
    cam2 = DBCamera(id=2, name="Test Cam 2", rtsp_url="rtsp://test2", is_active=False)
    cam3 = DBCamera(id=3, name="Test Cam 3 Active", rtsp_url="rtsp://test3", is_active=True)
    db.add_all([cam1, cam2, cam3])
    db.commit()
    return [cam1, cam2, cam3]

def get_auth_headers(test_client_fixture: TestClient, db_session_fixture: Session) -> dict:
    # Helper to login and get auth headers
    _, admin_pass = create_test_admin_user(db_session_fixture, username="testcamuser")
    login_response = test_client_fixture.post("/auth/token", data={"username": "testcamuser", "password": admin_pass})
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_list_cameras_authenticated(test_client_fixture: TestClient, db_session_fixture: Session):
    headers = get_auth_headers(test_client_fixture, db_session_fixture)
    seeded_cameras = seed_cameras(db_session_fixture) # Seed cameras
    
    # Important: CameraManager is loaded once at startup.
    # If these tests run after CameraManager has already loaded with an empty DB,
    # it won't see newly seeded cameras unless it's reloaded or cameras are added via an API.
    # The conftest.py fixture for db_session_fixture *does* try to patch
    # camera_manager_global.db_session. This should mean CameraManager uses the test session.
    # We also need to ensure CameraManager._load_cameras() is called with the test data.
    # One way is to re-call it, or ensure the CameraManager is fresh for the test.
    # For now, let's assume the patch in conftest works and CameraManager will see the data.
    # A better fix would be to make CameraManager re-loadable or a fixture itself.

    response = test_client_fixture.get("/api/cameras", headers=headers)
    assert response.status_code == 200, response.text
    cameras_list = response.json()
    assert isinstance(cameras_list, list)
    
    # CameraManager loads only active cameras. We seeded 2 active cameras.
    # is_running will be False as cv2.VideoCapture won't connect to dummy RTSP.
    active_seeded_cameras = [c for c in seeded_cameras if c.is_active]
    assert len(cameras_list) == len(active_seeded_cameras) 

    for cam_info in cameras_list:
        assert cam_info["is_running"] == False # Expected in test environment
        assert cam_info["name"] in [c.name for c in active_seeded_cameras]

def test_list_cameras_unauthenticated(test_client_fixture: TestClient):
    response = test_client_fixture.get("/api/cameras")
    assert response.status_code == 401, response.text

def seed_camera_with_settings(db: Session, camera_id: int, name: str, is_active: bool = True) -> DBCamera:
    # Ensure camera exists or create it
    cam = db.query(DBCamera).filter(DBCamera.id == camera_id).first()
    if not cam:
        cam = DBCamera(id=camera_id, name=name, rtsp_url=f"rtsp://cam{camera_id}", is_active=is_active)
        db.add(cam)
        # Must commit here if settings relies on camera.id via FK immediately
        db.commit() 
        db.refresh(cam)

    # Ensure settings exist for this camera
    settings = db.query(DBCameraSettings).filter(DBCameraSettings.camera_id == cam.id).first()
    if not settings:
        settings = DBCameraSettings(
            camera_id=cam.id, 
            resolution="1280x720", 
            brightness=50,
            # Initialize other fields as per your model's defaults or test needs
            night_vision=False,
            autofocus=True,
            contrast=50,
            saturation=50,
            sharpness=50,
            microphone_enabled=True,
            motion_detection_enabled=False,
            motion_sensitivity=30,
            motion_min_area=500,
            record_on_motion=False,
            object_detection_enabled=False
        )
        db.add(settings)
        db.commit()
    db.refresh(cam) # Refresh cam to potentially load its settings relationship
    return cam

def test_get_camera_settings_authenticated(test_client_fixture: TestClient, db_session_fixture: Session):
    headers = get_auth_headers(test_client_fixture, db_session_fixture)
    # Seed a camera and its settings
    camera = seed_camera_with_settings(db_session_fixture, camera_id=20, name="SettingsCamGet")
    
    # Reload camera manager to ensure it picks up the new camera and settings
    # This is now handled by the updated conftest.py's test_client_fixture
    # from main import camera_manager_global 
    # camera_manager_global.reload_cameras_from_db()

    response = test_client_fixture.get(f"/api/settings/{camera.id}", headers=headers)
    assert response.status_code == 200, response.text
    retrieved_settings = CameraSettingsResponse(**response.json())
    assert retrieved_settings.camera_id == camera.id
    assert retrieved_settings.brightness == 50 # Check one of the default seeded values

def test_update_camera_settings_authenticated(test_client_fixture: TestClient, db_session_fixture: Session):
    headers = get_auth_headers(test_client_fixture, db_session_fixture)
    camera = seed_camera_with_settings(db_session_fixture, camera_id=21, name="SettingsCamUpdate")

    # from main import camera_manager_global # Already imported if running sequentially in a class
    # camera_manager_global.reload_cameras_from_db() # Handled by conftest

    update_payload = {
        "brightness": 75,
        "night_vision": True,
        "motion_detection_enabled": True,
        "object_detection_enabled": True # Test a new field
    }
    response = test_client_fixture.post(f"/api/settings/{camera.id}", headers=headers, json=update_payload)
    assert response.status_code == 200, response.text
    updated_settings_resp = CameraSettingsResponse(**response.json())
    assert updated_settings_resp.brightness == 75
    assert updated_settings_resp.night_vision == True
    assert updated_settings_resp.motion_detection_enabled == True
    assert updated_settings_resp.object_detection_enabled == True

    # Verify in DB directly
    db_settings = db_session_fixture.query(DBCameraSettings).filter(DBCameraSettings.camera_id == camera.id).first()
    assert db_settings is not None
    assert db_settings.brightness == 75
    assert db_settings.night_vision == True
    assert db_settings.motion_detection_enabled == True
    assert db_settings.object_detection_enabled == True

    # Verify that ManagedCamera instance (if camera is active) has reloaded settings
    from main import camera_manager_global # For direct inspection
    managed_cam = camera_manager_global.get_camera(camera.id)
    if managed_cam and managed_cam.settings: # Camera must be active to be in manager
         assert managed_cam.settings.brightness == 75
         assert managed_cam.settings.night_vision == True
         assert managed_cam.settings.motion_detection_enabled == True
         assert managed_cam.settings.object_detection_enabled == True
    elif camera.is_active: # If camera was active but not found in manager, that's an issue
        assert False, f"Active camera {camera.id} not found in CameraManager after settings update."

def test_get_settings_for_non_existent_camera(test_client_fixture: TestClient, db_session_fixture: Session):
    headers = get_auth_headers(test_client_fixture, db_session_fixture)
    response = test_client_fixture.get("/api/settings/99999", headers=headers) # ID that should not exist
    assert response.status_code == 404, response.text

def test_take_snapshot_authenticated(test_client_fixture: TestClient, db_session_fixture: Session):
    headers = get_auth_headers(test_client_fixture, db_session_fixture)
    camera = seed_camera_with_settings(db_session_fixture, camera_id=30, name="SnapshotCam")

    from app.main import camera_manager_global # To mock methods on the actual instance
    camera_manager_global.reload_cameras_from_db() # Ensure CM is up-to-date
    
    dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8) # A fake image frame

    # Mock os.makedirs, cv2.imwrite, and the frame fetching part of CameraManager
    with mock.patch('os.makedirs') as mock_makedirs, \
         mock.patch('cv2.imwrite', return_value=True) as mock_cv_imwrite, \
         mock.patch.object(camera_manager_global, 'get_frame_from_camera', return_value=dummy_frame) as mock_get_frame:
        
        response = test_client_fixture.post(f"/api/cameras/{camera.id}/snapshot", headers=headers)
        
        assert response.status_code == 200, response.text
        json_data = response.json()
        assert json_data["message"] == "Snapshot saved"
        assert "filename" in json_data
        assert json_data["filename"].startswith(f"snapshot_cam{camera.id}_")
        
        # Check that the mocks were called as expected
        mock_makedirs.assert_called_once_with(app_settings.SNAPSHOT_DIR, exist_ok=True)
        mock_get_frame.assert_called_once_with(camera.id)
        # cv2.imwrite is called with (filepath, frame)
        # expected_filepath = os.path.join(app_settings.SNAPSHOT_DIR, json_data["filename"])
        # mock_cv_imwrite.assert_called_once_with(expected_filepath, dummy_frame)
        # Comparing numpy arrays with assert_called_with can be tricky.
        # Check that it was called, and then you can inspect mock_cv_imwrite.call_args for details if needed.
        assert mock_cv_imwrite.called

def test_start_recording_authenticated(test_client_fixture: TestClient, db_session_fixture: Session):
    headers = get_auth_headers(test_client_fixture, db_session_fixture)
    camera = seed_camera_with_settings(db_session_fixture, camera_id=31, name="RecordStartCam")

    from app.main import camera_manager_global
    camera_manager_global.reload_cameras_from_db()
    
    managed_cam = camera_manager_global.get_camera(camera.id)
    assert managed_cam is not None, "Camera not loaded into CameraManager"

    # Mock the start_recording method of the specific ManagedCamera instance
    with mock.patch.object(managed_cam, 'start_recording', return_value=True) as mock_start_recording_method:
        response = test_client_fixture.post(f"/api/cameras/{camera.id}/recording/start", headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["message"] == "Recording started successfully"
        mock_start_recording_method.assert_called_once()

def test_stop_recording_authenticated(test_client_fixture: TestClient, db_session_fixture: Session):
    headers = get_auth_headers(test_client_fixture, db_session_fixture)
    camera = seed_camera_with_settings(db_session_fixture, camera_id=32, name="RecordStopCam")

    from app.main import camera_manager_global
    camera_manager_global.reload_cameras_from_db()
    managed_cam = camera_manager_global.get_camera(camera.id)
    assert managed_cam is not None, "Camera not loaded"

    # To test stop, we need to simulate it's recording
    # Patch the 'is_recording' attribute and the 'stop_recording' method
    with mock.patch.object(managed_cam, 'is_recording', True, create=True), \
         mock.patch.object(managed_cam, 'stop_recording', return_value=True) as mock_stop_recording_method:
        
        response = test_client_fixture.post(f"/api/cameras/{camera.id}/recording/stop", headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["message"] == "Recording stopped successfully"
        mock_stop_recording_method.assert_called_once()

def test_list_events_authenticated(test_client_fixture: TestClient, db_session_fixture: Session):
    headers = get_auth_headers(test_client_fixture, db_session_fixture)
    camera = seed_camera_with_settings(db_session_fixture, camera_id=33, name="EventLogCam")

    from app.main import camera_manager_global
    camera_manager_global.reload_cameras_from_db() 

    # Seed events using CameraManager's method
    event_desc1 = "Test event 1 for listing"
    event_desc2 = "Another event for camera 33"
    camera_manager_global.record_camera_event(camera.id, "test_event_type_1", event_desc1)
    camera_manager_global.record_camera_event(camera.id, "test_event_type_2", event_desc2)

    response = test_client_fixture.get("/api/events", headers=headers)
    assert response.status_code == 200, response.text
    events_list = response.json()
    assert isinstance(events_list, list)
    
    # Check if our seeded events are present (API returns in descending timestamp order)
    descriptions_in_response = [e["message"] for e in events_list] # 'message' is the key in API for event_description
    assert event_desc1 in descriptions_in_response
    assert event_desc2 in descriptions_in_response
    
    found_event1 = any(e["message"] == event_desc1 and e["camera_id"] == camera.id for e in events_list)
    assert found_event1, "Seeded event 1 not found or camera_id mismatch"
