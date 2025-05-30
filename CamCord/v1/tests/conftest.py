# CamCord/v1/tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession # Renamed for clarity
import os
import sys

# Add app directory to sys.path to allow imports from app
APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app'))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# Now app modules can be imported
from database import Base, get_db # get_db is the dependency we'll override
from main import app, camera_manager_global # Import main FastAPI app and globals
# from config import settings as app_settings # To potentially override settings too

# Override database URL for testing (use in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def db_engine_fixture():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine) # Create tables in the test DB
    yield engine
    Base.metadata.drop_all(bind=engine) # Optional: drop tables after session


@pytest.fixture(scope="function")
def db_session_fixture(db_engine_fixture):
    """Yields a SQLAlchemy session for a single test function with transaction rollback."""
    connection = db_engine_fixture.connect()
    transaction = connection.begin()
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    db = TestSessionLocal()

    # Store the original CameraManager db_session and replace it
    # This is crucial for tests that indirectly use CameraManager's session
    original_cm_db_session = None
    if hasattr(camera_manager_global, 'db_session'): # Check if attribute exists
         original_cm_db_session = camera_manager_global.db_session
         camera_manager_global.db_session = db

    yield db

    db.close()
    transaction.rollback()
    connection.close()

    # Restore CameraManager's original session
    if hasattr(camera_manager_global, 'db_session') and original_cm_db_session is not None: # Check again before restoring
        camera_manager_global.db_session = original_cm_db_session


@pytest.fixture(scope="function")
def test_client_fixture(db_session_fixture: SQLAlchemySession):
    """Provides a TestClient for API testing, with DB dependency overridden."""

    def override_get_db():
        try:
            yield db_session_fixture
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Ensure CameraManager uses the test DB session for its operations AND reloads its state
    # The camera_manager_global.db_session is already patched by db_session_fixture.
    # Now, explicitly reload its camera list using this test session.
    if hasattr(camera_manager_global, 'reload_cameras_from_db'):
        camera_manager_global.reload_cameras_from_db()

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
