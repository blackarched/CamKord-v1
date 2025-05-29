from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from .user_auth_backend import get_current_user # Corrected import
from .dashboard_backend import router as api_router
from .user_auth_backend import auth_router
from .config import settings # Added import for settings
from .camera_manager import CameraManager # Added import
from .database import SessionLocal # Added import

app = FastAPI(title="SecurityCam Suite API")

# Global CameraManager instance
# This session is dedicated to the CameraManager's lifetime
db_session_for_camera_manager = SessionLocal() 
camera_manager_global = CameraManager(db_session=db_session_for_camera_manager)

@app.on_event("shutdown")
def shutdown_event():
    print("Application shutdown: Releasing camera resources...")
    camera_manager_global.shutdown()
    db_session_for_camera_manager.close()
    print("CameraManager shut down and its DB session closed.")

# Dependency to provide the CameraManager instance
def get_camera_manager_dependency():
    return camera_manager_global

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS, # Use settings
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

app.include_router(api_router) # This has /api prefix from its own file
app.include_router(auth_router, tags=["Authentication"]) # Routes in auth_router already have /auth

@app.websocket("/ws/stream/{camera_id}")
async def stream_endpoint(websocket: WebSocket, camera_id: str, user=Depends(get_current_user)):
    await websocket.accept()
    # TODO: forward camera frames via WebSocket
    await websocket.close()