# CamKord-v1: Cyberpunk Security Camera Dashboard

CamKord-v1 is a refactored and enhanced security camera monitoring solution featuring a FastAPI backend and a cyberpunk-themed web frontend. It supports live streaming, recording, snapshots, motion detection, object detection, and configurable camera settings.

## Features

*   **Unified Backend:** Single FastAPI application serving both API and frontend.
*   **Cyberpunk Themed UI:** Custom themed frontend for a unique visual experience.
*   **Authentication:** Secure JWT-based authentication for API access.
*   **Camera Management:**
    *   Support for multiple RTSP cameras (USB camera support is a planned enhancement).
    *   Live video streaming via WebSocket (primary).
    *   Snapshots and Video Recording (MP4 format).
    *   Individual camera settings: Resolution, Night Vision, Autofocus, Brightness, Contrast, Saturation, Sharpness, Motion Detection, Object Detection, etc.
    *   Live reload of settings to active camera instances.
*   **Event System:**
    *   Motion detection with configurable sensitivity and minimum area.
    *   Events (motion, snapshots) logged to the database.
    *   Optional: Automatic recording triggered by motion.
*   **Object Detection:** Integrated YOLOv4-tiny for real-time object detection on video streams (toggleable per camera).
*   **Ease of Use:** Startup scripts (`start_backend.sh`, `start_backend.bat`) provided for easier configuration and launch. Frontend served by the backend.
*   **API Documentation:** Self-documenting API via FastAPI (`/docs`, `/redoc`).

## Prerequisites

*   Python 3.8+
*   pip (Python package installer)
*   (Optional, for some `cv2.VideoCapture` backends on Linux) `libgl1-mesa-glx` or similar (e.g., `sudo apt-get install libgl1-mesa-glx`).

## Project Structure Overview

```
CamKord-v1/
├── app/                  # FastAPI backend application
│   ├── main.py           # Main application entry point, serves frontend
│   ├── database.py       # SQLAlchemy models, DB initialization, event logging
│   ├── schemas.py        # Pydantic schemas for API validation
│   ├── config.py         # Application configuration (Pydantic BaseSettings)
│   ├── camera_manager.py # Core camera handling logic (ManagedCamera, CameraManager)
│   ├── object_detector.py# YOLOv4-tiny object detection logic
│   ├── user_auth_backend.py # JWT Authentication logic and routes
│   ├── dashboard_backend.py # Main API routes (cameras, settings, etc.)
│   ├── models/           # Directory for object detection model files (.cfg, .weights, .names)
│   └── data/             # Default directory for SQLite DB, logs (auto-created)
├── frontend/             # Frontend files
│   ├── index.html        # Main HTML page
│   ├── app.js            # Core JavaScript application logic
│   ├── cyberpunk-theme.css # Cyberpunk theme styles
│   ├── style.css         # Minimal supplementary styles
│   └── fonts/            # Directory for custom font files (user must add files here)
├── tests/                # Pytest tests
├── start_backend.sh      # Startup script for Linux/macOS
├── start_backend.bat     # Startup script for Windows
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

## Setup & Installation

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url> # Or download and extract the ZIP
    cd CamKord-v1 
    ```

2.  **Install Python Dependencies:**
    It's highly recommended to use a Python virtual environment.
    ```bash
    # Create a virtual environment (e.g., named 'venv')
    python3 -m venv venv 
    # Activate it
    # On Linux/macOS:
    source venv/bin/activate
    # On Windows (cmd.exe):
    # venv\Scripts\activate.bat
    # On Windows (PowerShell):
    # .\venv\Scripts\Activate.ps1

    # Install dependencies
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables (Crucial First Step):**
    Before running the application for the first time, you **must** edit either `start_backend.sh` (for Linux/macOS) or `start_backend.bat` (for Windows) located in the `CamCord/v1/` directory. Set the following environment variables within the script:
    *   `SECRET_KEY`: **This is critical for security.** Replace `"!!!REPLACE_WITH_YOUR_STRONG_RANDOM_KEY!!!"` with a strong, random string. You can generate one using `openssl rand -hex 32` (on Linux/macOS) or a similar password generation tool.
    *   `CAMERA_SUITE_ADMIN_PASS`: Replace `"!!!REPLACE_WITH_YOUR_ADMIN_PASSWORD!!!"` with the desired password for the initial 'admin' user. If you leave this as the placeholder, the default 'admin' user will **not** be automatically created, and you would need to create a user through other means if user creation APIs are developed.
    *   `CORS_ALLOWED_ORIGINS`: This defaults to `"http://localhost:8000,http://127.0.0.1:8000"` which is suitable when the backend serves the frontend. If you plan to serve the frontend from a different domain or port in development or production, update this comma-separated list accordingly (e.g., `"https://your.frontend.domain.com"`).

4.  **Add Font Files (Required for Cyberpunk Theme):**
    *   Create the directory `CamCord/v1/frontend/fonts/` if it doesn't exist.
    *   Place the following font files into this directory:
        *   `BlenderProBook.woff2`
        *   `Oxanium.woff2`
        *   `Cyberpunk.otf`
    *   These are referenced by `cyberpunk-theme.css`. You will need to obtain these font files separately (e.g., from the original cyberpunk-css GitHub project or other font distribution sites that allow their use).

5.  **Add Object Detection Model Files (Required for Object Detection Feature):**
    *   Create the directory `CamCord/v1/app/models/` if it doesn't exist.
    *   Place the following files into this directory:
        *   `yolov4-tiny.cfg`
        *   `yolov4-tiny.weights`
        *   `coco.names`
    *   These can typically be downloaded from official sources for YOLOv4-tiny (e.g., AlexeyAB's Darknet repository for `.cfg` and `.names`, and the YOLO website or Darknet project releases for `.weights`). The `CamCord/v1/app/object_detector.py` file contains example download URLs in its test block. Object detection will be disabled if these files are not found.

## Running the Application

1.  **Make the startup script executable (Linux/macOS only):**
    From the `CamKord/v1/` directory:
    ```bash
    chmod +x start_backend.sh
    ```
2.  **Run the appropriate script from the `CamKord/v1/` directory:**
    *   **Linux/macOS:** `./start_backend.sh`
    *   **Windows:** `start_backend.bat`

3.  **Access the Application:**
    *   Once the server starts (you should see Uvicorn startup messages), open your web browser and navigate to: `http://localhost:8000/`
    *   If you configured `CAMERA_SUITE_ADMIN_PASS` in the startup script, you can log in with:
        *   Username: `admin`
        *   Password: The password you set.

4.  **API Documentation:**
    When the application is running, you can access:
    *   Swagger UI (interactive API docs): `http://localhost:8000/docs`
    *   ReDoc (alternative API docs): `http://localhost:8000/redoc`

## Key Environment Variables

The application behavior can be customized via environment variables set in the startup scripts or your system environment. Key variables are defined in `CamCord/v1/app/config.py` and include:

*   `SECRET_KEY`: **Required.** JWT signing key.
*   `CAMERA_SUITE_ADMIN_PASS`: Password for the default 'admin' user created on first run.
*   `CORS_ALLOWED_ORIGINS`: Comma-separated list of allowed origins for Cross-Origin Resource Sharing.
*   `DATABASE_URL`: Database connection string. (Defaults to `sqlite:///./data/camera_suite.db` relative to the `app` directory).
*   `RECORDING_DIR`: Directory to save video recordings. (Defaults to `recordings` relative to `app`).
*   `SNAPSHOT_DIR`: Directory to save snapshots. (Defaults to `snapshots` relative to `app`).
*   `LOG_DIR`: Directory for general logs. (Defaults to `logs` relative to `app`).
*   Refer to `config.py` for other less critical configuration options like default camera resolution, supported resolutions, etc.
```
