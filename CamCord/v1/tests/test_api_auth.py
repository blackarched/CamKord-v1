# CamCord/v1/tests/test_api_auth.py
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import os

# Assuming conftest.py correctly adds 'app' to sys.path OR pytest.ini handles pythonpath
from database import User as DBUser
from config import settings as app_settings # Not strictly needed here but good for consistency

# Helper to create admin user
def create_test_admin_user(db: Session, username="admin", password_override=None):
    admin_pass = password_override or os.getenv("CAMERA_SUITE_ADMIN_PASS", "testadmin123")

    admin_user = db.query(DBUser).filter(DBUser.username == username).first()
    if not admin_user:
        hashed_pw = DBUser.hash_password(admin_pass)
        admin_user = DBUser(username=username, password_hash=hashed_pw, is_admin=True)
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
    return admin_user, admin_pass


def test_login_for_access_token(test_client_fixture: TestClient, db_session_fixture: Session):
    _, admin_pass = create_test_admin_user(db_session_fixture, username="testloginuser")

    response = test_client_fixture.post("/auth/token", data={"username": "testloginuser", "password": admin_pass})
    assert response.status_code == 200, response.text
    json_response = response.json()
    assert "access_token" in json_response
    assert json_response["token_type"] == "bearer"

def test_login_failed_invalid_credentials(test_client_fixture: TestClient, db_session_fixture: Session):
    create_test_admin_user(db_session_fixture, username="testloginfailuser")
    response = test_client_fixture.post("/auth/token", data={"username": "testloginfailuser", "password": "wrongpassword"})
    assert response.status_code == 401, response.text
    assert response.json()["detail"] == "Incorrect username or password"

def test_read_users_me_valid_token(test_client_fixture: TestClient, db_session_fixture: Session):
    _, admin_pass = create_test_admin_user(db_session_fixture, username="testmeuser")
    login_response = test_client_fixture.post("/auth/token", data={"username": "testmeuser", "password": admin_pass})
    token = login_response.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    response = test_client_fixture.get("/auth/me", headers=headers)
    assert response.status_code == 200, response.text
    json_response = response.json()
    assert json_response["username"] == "testmeuser"
    assert json_response["is_admin"] == True

def test_read_users_me_invalid_token(test_client_fixture: TestClient):
    headers = {"Authorization": "Bearer invalidtoken"}
    response = test_client_fixture.get("/auth/me", headers=headers)
    assert response.status_code == 401, response.text

def test_read_users_me_no_token(test_client_fixture: TestClient):
    response = test_client_fixture.get("/auth/me")
    assert response.status_code == 401, response.text # FastAPI's OAuth2PasswordBearer handles this
