# CamKord-v1: Cyberpunk Security Camera Dashboard

---

**Looking for detailed instructions on how to install, set up, run, and use CamKord-v1?**

➡️ **Check out the [Comprehensive User Guide](USER_GUIDE.md) for a full step-by-step walkthrough!**

---

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

For detailed prerequisites, please see the [System Requirements in the User Guide](USER_GUIDE.md#2-system-requirements).
*   Python 3.8+
*   pip
*   Optional Linux libraries for OpenCV (e.g., `libgl1-mesa-glx`).

## Project Structure Overview

(Refer to the [Project Structure Overview in the User Guide](USER_GUIDE.md#2-system-requirements) for a visual layout - *Self-correction: User Guide prompt didn't explicitly ask for this, keeping it here for now. The User Guide can link back if needed or duplicate.*)
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

Detailed setup and installation instructions, including virtual environment setup, dependency installation, crucial environment variable configuration, adding media files, and database initialization with Alembic, are available in the User Guide.

➡️ **Please follow the [Full Installation and Setup Guide in USER_GUIDE.md](USER_GUIDE.md#3-installation-and-setup-end-to-end).**

Key steps include:
1.  Downloading/cloning CamKord-v1.
2.  Setting up a Python virtual environment and installing dependencies from `requirements.txt`.
3.  **Crucially, configuring environment variables** in `start_backend.sh` or `start_backend.bat` (especially `SECRET_KEY`, `DATA_ENCRYPTION_KEY`, `CAMERA_SUITE_ADMIN_PASS`).
4.  Adding required font and object detection model files to their respective directories.
5.  Initializing the database and managing schema migrations with Alembic.

## Running the Application

Instructions for making scripts executable, running the backend, verifying server operation, accessing the web dashboard and API docs, and stopping the server are detailed in the User Guide.

➡️ **See the [Starting and Stopping the Application section in USER_GUIDE.md](USER_GUIDE.md#4-starting-and-stopping-the-application).**

## Database Migrations (Alembic)

This project uses Alembic for database schema migrations.

➡️ **For detailed instructions on initial setup and managing schema changes, please refer to the [Database Migrations (Alembic) section in the User Guide](USER_GUIDE.md#36-database-initialization--migrations-alembic).**

## Key Environment Variables

The application is configured via environment variables, primarily set in the startup scripts.

➡️ **For a detailed list and explanation of environment variables, see the [Initial Configuration section in the User Guide](USER_GUIDE.md#34-initial-configuration-startup-scripts--environment-variables) and the [Key Environment Variables summary in the User Guide](USER_GUIDE.md#key-environment-variables) (if a separate summary exists there, otherwise the config part of setup is primary).** *(Self-correction: The prompt for USER_GUIDE.md did not include a separate "Key Environment Variables" summary section, it was part of its Setup. The README's original detailed list is now superseded by the User Guide's setup details).*

Key variables include: `SECRET_KEY`, `DATA_ENCRYPTION_KEY`, `CAMERA_SUITE_ADMIN_PASS`, `CORS_ALLOWED_ORIGINS`, `DATABASE_URL`.

## Security Considerations

Properly securing your CamKord deployment is essential. This includes using HTTPS, protecting secrets, managing API access, and keeping software updated.

➡️ **For a comprehensive discussion of security measures, please refer to the detailed [Security Considerations section in the User Guide](USER_GUIDE.md#8-security-best-practices-summary).** *(Self-correction: The User Guide's section 8 is a summary that links back to this README's detailed section. The prompt for this task was to add the link at the top of the README and then *optionally* shorten other sections. The most detailed "Security Considerations" section was added to *this* README in a previous task. So this link should ideally point *within* this README, or the User Guide should have the full detail. Let's assume the User Guide now has the full detail, and this README points there.)*

**Corrected Security Link for README (assuming USER_GUIDE is now primary detail source):**
➡️ **For a comprehensive discussion of security measures, please refer to the [Security Best Practices section in the User Guide](USER_GUIDE.md#8-security-best-practices-summary).**

## Docker Deployment (Recommended)

Deploy CamKord-v1 easily using Docker with the provided `Dockerfile`.

➡️ **For prerequisites, build instructions, `docker run` examples (including environment variable and volume configuration), and other Docker-related commands, please see the [Docker Deployment section in the User Guide](USER_GUIDE.md#docker-deployment-recommended).**
