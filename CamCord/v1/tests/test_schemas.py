# CamCord/v1/tests/test_schemas.py
import pytest
from pydantic import ValidationError

# Assuming conftest.py correctly adds 'app' to sys.path OR pytest.ini handles pythonpath
from schemas import CameraSettingsUpdate, CameraSettingsResponse, CameraInfo

def test_camera_settings_update_defaults():
    settings = CameraSettingsUpdate()
    assert settings.motion_detection_enabled == False
    assert settings.brightness == 50
    assert settings.object_detection_enabled == False
    assert settings.resolution == "1280x720"

def test_camera_settings_update_custom_valid():
    data = {
        "resolution": "1920x1080",
        "night_vision": True,
        "brightness": 75,
        "motion_sensitivity": 60,
        "object_detection_enabled": True
    }
    settings = CameraSettingsUpdate(**data)
    assert settings.resolution == "1920x1080"
    assert settings.night_vision == True
    assert settings.brightness == 75
    assert settings.motion_sensitivity == 60
    assert settings.object_detection_enabled == True

def test_camera_settings_update_invalid_value():
    with pytest.raises(ValidationError):
        CameraSettingsUpdate(brightness=151)

    with pytest.raises(ValidationError):
        CameraSettingsUpdate(motion_sensitivity=-1)

def test_camera_info_instantiation():
    # Basic test to ensure CameraInfo can be instantiated
    info = CameraInfo(
        id=1,
        name="Test Cam",
        is_running=True,
        motion_detection_enabled=False,
        object_detection_enabled=True
    )
    assert info.name == "Test Cam"
    assert info.object_detection_enabled == True
