# CamKord-v1 User Guide

## 1. Introduction

Welcome to CamKord-v1! This guide provides comprehensive instructions for installing, configuring, running, and using the CamKord security camera monitoring system.

**What is CamKord-v1?**

CamKord-v1 is a versatile and feature-rich solution designed for monitoring live video feeds from network cameras (primarily RTSP streams). It combines a powerful Python-based backend built with FastAPI and a dynamic, cyberpunk-themed web frontend for user interaction. Whether you're looking to monitor a few cameras for personal use or need a base for a more extensive surveillance setup, CamKord aims to provide a robust and extensible platform.

**Key Features Overview:**

*   **Web-Based Dashboard:** Access and control your cameras from anywhere via a web browser.
*   **Cyberpunk Aesthetic:** A unique, visually engaging user interface.
*   **Secure Access:** JWT-based authentication protects your system.
*   **Live Video Streaming:** Real-time video feeds using efficient WebSocket technology.
*   **Camera Management:** (Primarily API-driven for now for CRUD) Add, configure, and manage multiple cameras.
*   **Comprehensive Camera Settings:** Adjust resolution, brightness, contrast, saturation, sharpness, night vision, autofocus, microphone status, motion detection parameters, and object detection toggle per camera via the UI.
*   **Recording & Snapshots:** Capture important moments with video recording and still image snapshots. Snapshots can be encrypted at rest if configured.
*   **Intelligent Monitoring:**
    *   **Motion Detection:** Built-in motion detection with configurable sensitivity and minimum area per camera; can trigger recordings and logs events.
    *   **Object Detection:** Integrated YOLOv4-tiny for identifying common objects in video streams (toggleable per camera).
*   **Event Logging:** Key events like motion detection, snapshots taken/deleted, and recordings started/stopped/deleted are logged to a database.
*   **Ease of Deployment:** Simplified startup using provided shell/batch scripts, and Docker support for containerized deployment.
*   **Extensible API:** A well-documented FastAPI backend (via `/docs` and `/redoc`) allows for integration and custom extensions.
*   **Database Migrations:** Uses Alembic for managing database schema changes.

**Who is this guide for?**

This guide is intended for end-users and administrators of the CamKord-v1 system. It covers:
*   Users who want to set up and run CamKord for monitoring.
*   Administrators responsible for installation, configuration, and maintenance.
*   Developers who might want to understand its operational aspects before diving into the code (for code-specific details, see `README.md` and the source).

---

## 2. System Requirements

To ensure CamKord-v1 runs smoothly, please make sure your system meets the following requirements.

**Operating System:**

*   **Server (Backend):**
    *   Linux (Recommended, e.g., Ubuntu, Debian, CentOS)
    *   Windows 10/11 or Windows Server 2016 and later (for running `.bat` script)
    *   macOS
*   **Client (Web Dashboard):**
    *   Any modern desktop operating system (Windows, macOS, Linux) with a compatible web browser.

**Python Environment (for running backend without Docker):**

*   Python: Version 3.8 to 3.11 recommended.
*   pip: Python package installer (usually comes with Python).
*   Virtual Environment: Strongly recommended (e.g., `venv` module).

**Web Browser (for accessing dashboard):**

*   Latest versions of Chrome, Firefox, Edge, or Safari.
*   Must support WebSockets and modern JavaScript (ES6+).

**Hardware Considerations (Server):**

*   **CPU:**
    *   Minimum: Dual-core processor.
    *   Recommended: Quad-core processor or better, especially if handling multiple cameras or running object detection.
*   **RAM:**
    *   Minimum: 2GB RAM (for 1-2 cameras without heavy processing).
    *   Recommended: 4GB RAM for a few cameras; 8GB+ RAM if running object detection on multiple streams or handling many cameras. Object detection, especially on CPU, can be memory and CPU intensive.
*   **Storage:**
    *   Sufficient disk space for the operating system, Python environment, CamKord application files.
    *   Additional significant disk space for storing video recordings and snapshots. Required space depends on the number of cameras, resolution, recording duration, and retention policies.
*   **Network:**
    *   Stable network connection for the server.
    *   Sufficient bandwidth if cameras are remote or if many clients will be viewing streams simultaneously.
    *   Wired Ethernet connection is recommended for the server.

**System Dependencies (primarily for OpenCV on Linux when not using Docker):**

*   On Linux systems, OpenCV (used for video processing) often requires certain shared libraries. A common one is `libgl1-mesa-glx`. You can usually install it via your package manager:
    ```bash
    sudo apt-get update && sudo apt-get install -y libgl1-mesa-glx
    ```
    Other libraries like `ffmpeg` (installed via Dockerfile if using Docker, may be needed on host if not using Docker) might be required for handling specific video codecs from RTSP streams. Consult OpenCV documentation for your specific OS if you encounter issues with video capture.

---

## 3. Installation and Setup (End-to-End)

This section will guide you through the complete installation and initial setup process for CamKord-v1. Please follow these steps carefully.

### 3.1. Downloading CamKord

*   **Option 1: Using Git (Recommended)**
    If you have Git installed, you can clone the repository for the latest version:
    ```bash
    git clone <repository_url_placeholder> # Replace with actual CamKord-v1 repository URL
    cd CamKord-v1
    ```
*   **Option 2: Downloading ZIP Archive**
    If the project is available as a ZIP file (e.g., from a release page), download it and extract it to your desired location. Navigate into the main `CamKord-v1` directory.

### 3.2. Setting up a Python Virtual Environment

Using a Python virtual environment is strongly recommended to manage dependencies and avoid conflicts with other Python projects or system-wide packages.

*   **Navigate to the project root directory** (`CamKord-v1/` if you cloned/extracted).
*   **Create the virtual environment** (common name is `venv`):
    ```bash
    python3 -m venv venv  # Or just 'python' depending on your system's Python alias
    ```
*   **Activate the virtual environment:**
    *   **On Linux or macOS:**
        ```bash
        source venv/bin/activate
        ```
        Your shell prompt should change to indicate the active environment (e.g., `(venv) youruser@host:...$`).
    *   **On Windows (Command Prompt):**
        ```bat
        venv\Scripts\activate.bat
        ```
    *   **On Windows (PowerShell):**
        ```powershell
        .\venv\Scripts\Activate.ps1
        ```
        (If PowerShell script execution is disabled, you might need to run `Set-ExecutionPolicy Unrestricted -Scope Process` first, for that shell instance only).

    You'll need to activate the virtual environment every time you open a new terminal session to work on this project.

### 3.3. Installing Dependencies

Once your virtual environment is active, install the required Python packages:

*   Ensure you are in the `CamKord-v1/` directory where `requirements.txt` is located.
*   Run:
    ```bash
    pip install -r requirements.txt
    ```
    This will download and install all necessary libraries listed in the `requirements.txt` file (FastAPI, Uvicorn, SQLAlchemy, OpenCV, etc.).

### 3.4. Initial Configuration (Startup Scripts & Environment Variables)

CamKord-v1 is configured primarily through environment variables, which are conveniently set within platform-specific startup scripts. **This is a critical step for security and functionality.**

*   Navigate to the `CamKord-v1/` directory if you're not already there. You will find `start_backend.sh` (for Linux/macOS) and `start_backend.bat` (for Windows).
*   **Open the script relevant to your operating system in a text editor.**

You **MUST** set the following environment variables within the script before running it for the first time:

1.  **`SECRET_KEY`**:
    *   **Purpose:** This is a secret key used for signing JWT authentication tokens and other security-related functions. It must be kept confidential.
    *   **Action:** Replace `"!!!REPLACE_WITH_YOUR_STRONG_RANDOM_KEY!!!"` with a long, random, and unique string.
    *   **How to Generate (Linux/macOS example using OpenSSL):**
        ```bash
        openssl rand -hex 32
        ```
        Copy the output of this command and paste it as the value for `SECRET_KEY`.
    *   **How to Generate (Python interactive):**
        ```bash
        python -c "import secrets; print(secrets.token_hex(32))"
        ```
        Copy the output.

2.  **`DATA_ENCRYPTION_KEY`**:
    *   **Purpose:** This key is used for encrypting and decrypting snapshots stored on disk. It also must be kept highly confidential.
    *   **Action:** Find the line for `DATA_ENCRYPTION_KEY` in your startup script (if not present, add it, e.g., `export DATA_ENCRYPTION_KEY="..."` in `.sh` or `set "DATA_ENCRYPTION_KEY=..."` in `.bat`). Replace any placeholder with a newly generated Fernet key.
    *   **How to Generate (Python interactive):**
        ```bash
        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
        ```
        Copy the entire output string (it's a base64 encoded byte string) and set it as the value for `DATA_ENCRYPTION_KEY`.
    *   **Note:** If `DATA_ENCRYPTION_KEY` is not set or is invalid, snapshot encryption will be disabled, and snapshots will be saved unencrypted (a warning will be logged by the server).

3.  **`CAMERA_SUITE_ADMIN_PASS`**:
    *   **Purpose:** Sets the password for the default administrative user (username: `admin`) that will be created on the application's first run if it doesn't already exist.
    *   **Action:** Replace `"!!!REPLACE_WITH_YOUR_ADMIN_PASSWORD!!!"` with a strong, unique password.
    *   **Note:** If you leave this as the placeholder or an empty string, the default 'admin' user will **not** be automatically created. You would then need to create an admin user through other means (e.g., future user management API/UI, or direct database interaction).

4.  **`CORS_ALLOWED_ORIGINS`** (Cross-Origin Resource Sharing):
    *   **Purpose:** Controls which frontend URLs are allowed to make requests to the backend API.
    *   **Default (in scripts):** Usually `"http://localhost:8000,http://127.0.0.1:8000"`. This is suitable when the FastAPI backend serves the frontend directly on port 8000.
    *   **Action:**
        *   If you access the dashboard using a different hostname (even on the same machine, e.g., `http://my-pc-name:8000`), add that to the list.
        *   For production, replace this with the actual domain(s) your frontend will be served from (e.g., `"https://your.camkord.domain.com"`).
        *   Multiple origins are comma-separated.

5.  **(Optional) `DATABASE_URL`**:
    *   **Purpose:** Defines the connection string for the database.
    *   **Default:** The application defaults to using an SQLite database stored at `CamCord/v1/app/data/camera_suite.db`. The `app/data` directory will be created automatically if it doesn't exist.
    *   **Action:** For most initial uses, the default is fine. If you want to use a different SQLite file path or connect to a PostgreSQL or MySQL database, you can uncomment and set the `DATABASE_URL` in the startup script accordingly (e.g., `postgresql://user:pass@host:port/dbname`). Ensure you have the correct database drivers installed (e.g., `psycopg2-binary` for PostgreSQL) in `requirements.txt`.

**Save the changes to your startup script after setting these variables.**

### 3.5. Adding Essential Media Files

For the full visual experience and functionality, you need to add some files to the project directory manually.

*   **Font Files (for Cyberpunk Theme):**
    1.  Create the directory (if it doesn't already exist): `CamCord/v1/frontend/fonts/`
    2.  Obtain the following font files and place them into this `fonts/` directory:
        *   `BlenderProBook.woff2`
        *   `Oxanium.woff2`
        *   `Cyberpunk.otf`
    3.  These fonts are referenced in `cyberpunk-theme.css`. You may need to source them from their original distributors (e.g., the cyberpunk-css GitHub project might have links, or general font websites that license them for use). Without these, the dashboard will fall back to system default fonts, and the cyberpunk aesthetic will be incomplete.

*   **Object Detection Model Files (for YOLOv4-tiny):**
    1.  Create the directory (if it doesn't already exist): `CamCord/v1/app/models/`
    2.  Obtain the following model files and place them into this `models/` directory:
        *   `yolov4-tiny.cfg`
        *   `yolov4-tiny.weights`
        *   `coco.names`
    3.  These are standard files for the YOLOv4-tiny object detection model.
        *   The `.cfg` and `.names` files can usually be found in the official Darknet GitHub repository (e.g., under `cfg/` and `data/` respectively).
        *   The `.weights` file is a larger binary file; search for "yolov4-tiny.weights download" from official/trusted sources (e.g., links provided by AlexeyAB's Darknet repository or the official YOLO website).
        *   The `CamCord/v1/app/object_detector.py` file has a test block (`if __name__ == '__main__':`) that includes example download URLs for these files.
    4.  If these model files are not present, the Object Detection feature will be automatically disabled (a warning will be logged by the server).

### 3.6. Database Initialization & Migrations (Alembic)

The application uses SQLAlchemy for database interaction and Alembic for managing database schema migrations.

*   **Automatic Table Creation (First App Start):**
    When you start the CamKord application for the very first time (see "Starting the Application" below), the `init_db()` function in `app/main.py` will be called. This function attempts to create all necessary database tables based on the current SQLAlchemy models if they don't already exist. For a brand new setup with an empty database (e.g., the default `camera_suite.db` SQLite file that will be auto-created in `app/data/`), this is usually sufficient to get started quickly.

*   **Using Alembic for Schema Versioning (Recommended Best Practice):**
    For robust, long-term schema management, especially in production or if you plan to modify database models later, it's best to use Alembic to create the initial schema and manage all subsequent changes.
    1.  **Ensure `DATABASE_URL` is correctly set** in your environment/startup script.
    2.  **Navigate to the `app` directory:** All Alembic commands should be run from `CamCord/v1/app/` (where `alembic.ini` is located).
        ```bash
        cd CamCord/v1/app  # Or your equivalent path
        ```
    3.  **Generate an Initial Migration Script (If starting with a new, empty database and want Alembic to create schema):**
        If you are setting up the project for the first time and want Alembic to generate the script that creates all tables based on your current models:
        ```bash
        alembic revision -m "Create initial database schema from models" --autogenerate
        ```
        *   This command compares the models defined in `app.database.Base.metadata` with the (empty) database and generates a new script in `app/alembic/versions/`.
        *   **Important:** Always open and review this generated script. Alembic's autogenerate is powerful but might not capture every nuance perfectly.
    4.  **Apply the Migration to Create Schema:**
        ```bash
        alembic upgrade head
        ```
        This command applies all pending migrations. If it's the first migration, it will create all your tables.
    5.  **Alternative for Existing Databases or Post-`init_db()`:** If tables were already created by `init_db()` on the first app run, and you now want to start using Alembic for future changes, you can "stamp" the database to the latest Alembic revision without running any migrations that would try to re-create existing tables:
        ```bash
        # First, ensure your Alembic versions folder has an initial migration
        # that represents your current schema (you might need to generate one as above,
        # but DON'T apply it if tables exist).
        # Then, stamp:
        alembic stamp head
        ```
        This tells Alembic to assume all migrations up to `head` have been applied. Future model changes would then involve generating new revisions and upgrading.

    Refer to the "Database Migrations (Alembic)" section in `README.md` for more details on ongoing migration management after initial setup.

---

## 4. Starting and Stopping the Application

Once you have completed the Installation & Setup steps, you are ready to run the CamKord-v1 application.

### 4.1. Running the Startup Script

The backend server (which also serves the frontend web dashboard) is started using the scripts you configured in the setup phase.

*   **Navigate to the project root directory** (`CamKord-v1/`).
*   **Ensure your Python virtual environment is activated** if you installed dependencies there.
    *   Linux/macOS: `source venv/bin/activate`
    *   Windows (cmd): `venv\Scripts\activate.bat`
    *   Windows (PowerShell): `.\venv\Scripts\Activate.ps1`
*   **Run the appropriate script:**
    *   **For Linux or macOS:**
        1.  Make the script executable (only needs to be done once):
            ```bash
            chmod +x start_backend.sh
            ```
        2.  Run the script:
            ```bash
            ./start_backend.sh
            ```
    *   **For Windows:**
        Double-click `start_backend.bat` or run it from the command prompt:
        ```bash
        start_backend.bat
        ```

### 4.2. Verifying the Server is Running

After executing the startup script, you should see output in your terminal from the Uvicorn server. Key things to look for:

*   No immediate error messages.
*   Lines indicating the Uvicorn server is running, typically like:
    ```
    INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
    INFO:     Started reloader process [xxxxx] using statreload (if --reload is used, typically not in prod scripts)
    INFO:     Started server process [xxxxx]
    INFO:     Waiting for application startup.
    INFO:     Application startup complete.
    ```
*   You should also see log messages from CamKord, such as:
    *   `"Initializing database (if needed)..."`
    *   `"Database initialization check complete."`
    *   `"Attempting to serve static files from: <path_to_frontend>"`
    *   `"Frontend successfully mounted at '/'."`
    *   `"[CameraManager] Loaded X active cameras."` (if cameras are configured in DB and active)

If you see these messages and no major errors, the server is running.

### 4.3. Stopping the Server

*   To stop the CamKord backend server, go to the terminal window where it is running (where you executed the startup script).
*   Press `CTRL+C`.
*   You should see messages indicating the server is shutting down, including:
    *   `INFO:     Shutting down`
    *   `INFO:     Waiting for application shutdown.`
    *   `INFO:     Application shutdown complete.`
    *   `INFO:     Finished server process [xxxxx]`
    *   `[CameraManager] Shutting down...`
    *   `[CameraManager] All cameras released.`
    *   `CameraManager shut down and its DB session closed.`

---

## 5. Accessing and Using the Dashboard

With the CamKord server running, you can now access and use the web dashboard.

### 5.1. Accessing the Dashboard

*   Open a modern web browser (Chrome, Firefox, Edge, Safari recommended).
*   Navigate to the following URL:
    `http://localhost:8000/`
    (If you configured Uvicorn to run on a different host or port in the startup script, adjust the URL accordingly).

### 5.2. Logging In

*   You should be greeted by the **Login Access** screen with the cyberpunk theme.
*   **Username:** Enter `admin`.
*   **Password:** Enter the password you set for the `CAMERA_SUITE_ADMIN_PASS` environment variable in the startup script.
*   Click the **"ACCESS GRANTED [ENGAGE]"** button.
*   If login is successful, a "Login successful!" message will briefly appear, and you will be taken to the main dashboard.
*   If login fails, an error message will appear below the login button (e.g., "Login failed: Invalid credentials"). Double-check your username and password.

### 5.3. Dashboard Overview

The main dashboard interface is divided into several key areas, styled with a cyberpunk aesthetic:

*   **Header ("SYSTEM MONITOR"):** Displays the application title and the "LOGOUT" button.
*   **App Message Area:** A general area below the header where success messages, errors, or warnings are displayed.
*   **Main Content Area:**
    *   **Camera Configuration Panel (`CAMERA CONFIGURATION :: ID <ID>`):** This is where you manage settings for the selected camera. Includes inputs for resolution, image quality, features, and motion detection.
    *   **Live Feed Panel (`VISUAL FEED`):** Displays the live video stream from the selected camera. The image may have a subtle "glitch" effect as part of the theme.
    *   **Camera List Panel (`NETWORK ASSETS`):** Lists available cameras. Clicking a camera here selects it for viewing and configuration.
    *   **(Future Sections):** Placeholder areas for "Recording Archives" and "Event Logs" will be implemented to make these features accessible via the UI.

### 5.4. Camera Operations

*   **Selecting a Camera:**
    *   The "NETWORK ASSETS" panel lists cameras loaded by the system.
    *   The currently selected camera will be highlighted (e.g., yellow background with black text).
    *   To select a different camera, simply click on its name in the list.
    *   When a camera is selected:
        *   Its ID will appear in the "CAMERA CONFIGURATION" panel heading.
        *   Its live video stream will attempt to load in the "VISUAL FEED" panel via WebSocket.
        *   Its current settings will be fetched and displayed in the "CAMERA CONFIGURATION" panel.
*   **Viewing Live Video Stream (WebSocket):**
    *   Once a camera is selected, its video feed should start automatically in the "VISUAL FEED" panel.
    *   The `alt` text of the image area will show "Connecting..." then "Live feed from camera..." or an error if the stream cannot be established.
*   **Refreshing the Feed:**
    *   The "Refresh Feed [F5]" button (located above the settings panel) can be used to re-initiate the WebSocket connection for the currently selected camera's video stream.

### 5.5. Managing Camera Configuration (Settings Panel)

The "CAMERA CONFIGURATION" panel allows you to view and modify various settings for the **currently selected camera**.

*   **Accessing the Panel:** It's visible by default when you are logged in and a camera is selected.
*   **Populating Settings:** When you select a camera, its current settings are fetched from the server and displayed in the various input fields.
*   **Explanation of Settings:**
    *   **Image & Display:**
        *   `Resolution`: Select the desired resolution for the camera stream (e.g., "1280x720").
        *   `Brightness` (0-100): Adjusts image brightness.
        *   `Contrast` (0-100): Adjusts image contrast.
        *   `Saturation` (0-100): Adjusts image color saturation.
        *   `Sharpness` (0-100): Adjusts image sharpness.
    *   **Features:**
        *   `Night Vision`: Toggle checkbox to enable/disable night vision mode.
        *   `Auto Focus`: Toggle checkbox to enable/disable the camera's autofocus.
        *   `Microphone`: Toggle checkbox to enable/disable audio (Note: audio processing/streaming is not yet implemented in the backend/frontend, this is a placeholder for future).
        *   `Object Detection`: Toggle checkbox to enable/disable on-server YOLOv4-tiny object detection overlays. (Requires model files to be correctly installed).
    *   **Motion Detection:**
        *   `Enable`: Toggle checkbox to enable/disable motion detection.
        *   `Sensitivity` (0-100): Higher values mean more sensitive.
        *   `Min. Area` (e.g., 100-10000): Minimum size of a changed region to be considered motion.
        *   `Record on Motion`: Toggle checkbox to automatically start a video recording when motion is detected.
*   **Applying Changes:**
    *   After making any changes to the settings, click the **"Apply Configuration [S]"** button.
    *   This sends all displayed settings to the server for the selected camera.
    *   A message will appear in the "App Message Area" indicating success or failure.
    *   If successful, the video feed may briefly change as new settings are applied. The UI will update to reflect the saved state.

### 5.6. Using Snapshots

*   **Taking a Snapshot:**
    *   The backend API `POST /api/cameras/{camera_id}/snapshot` allows taking snapshots.
    *   *(User Guide Note: A dedicated button for this in the UI is a planned frontend enhancement.)*
    *   Snapshots are saved in the `app/snapshots/` directory (or as configured by `SNAPSHOT_DIR`).
    *   If `DATA_ENCRYPTION_KEY` is set, snapshots are saved encrypted (`.enc` extension).
*   **Viewing Snapshots:**
    *   Encrypted snapshots can be viewed via the `GET /api/snapshots/view/{filename_enc}` API endpoint.
    *   *(User Guide Note: A UI browser/viewer for snapshots is a planned frontend enhancement.)*

### 5.7. Using Recordings

*   **Starting and Stopping Recordings:**
    *   The backend API (`POST /api/cameras/{camera_id}/recording/start` and `.../stop`) allows this.
    *   *(User Guide Note: UI buttons for starting/stopping recordings per camera are a planned frontend enhancement.)*
    *   Recordings are saved as `.mp4` files in the `app/recordings/` directory.
*   **Managing and Playing Recordings:**
    *   Backend APIs exist to list, view, and delete recordings.
    *   *(User Guide Note: A "Recording Archives" section in the UI to list, filter, play back, and delete recordings is the next major planned frontend enhancement. The backend APIs for these functions are now in place.)*

### 5.8. Viewing Events

*   The system logs events (motion, snapshots, recording actions) to the database.
*   These can be accessed via the `GET /api/events` API endpoint.
*   *(User Guide Note: An "Event Log" or "Activity" viewer in the UI is a planned frontend enhancement.)*

### 5.9. Logging Out

*   Click the **"LOGOUT [ESC]"** button in the header.
*   This will clear your session, close any active video stream, and return you to the Login screen.

---

## 6. Administrative Tasks (Advanced Users / API)

While the main dashboard provides user-facing controls, some administrative tasks, like managing the camera inventory itself (adding new cameras, editing their core details like RTSP URLs, or deleting them), are currently performed via the backend API.

### 6.1. Overview of Admin Capabilities

An administrator (a user with `is_admin=true`, like the default 'admin' user) has permissions to:
*   Access all regular user functionalities.
*   Manage camera definitions (Create, Read, Update, Delete - CRUD) via API.
*   Delete recordings via API.
*   *(User Guide Note: A dedicated web UI for these admin tasks, particularly Camera CRUD, is a planned future enhancement.)*

### 6.2. Using the API for Camera Management (CRUD)

You can interact with the admin APIs using tools like `curl`, Postman, Insomnia, or any programming language that can make HTTP requests. The application also provides self-generating API documentation.

*   **Accessing API Documentation:**
    *   **Swagger UI:** `http://localhost:8000/docs`
    *   **ReDoc:** `http://localhost:8000/redoc`
    These interfaces allow you to explore all available API endpoints, view their request/response schemas, and even try them out directly from your browser (authentication is required for protected endpoints).

*   **Authentication for API:**
    1.  First, obtain a JWT token by sending a POST request to `/auth/token` with your admin username and password (as form data).
    2.  Copy the `access_token` from the response.
    3.  For subsequent API calls to protected admin endpoints, include an `Authorization` header: `Authorization: Bearer <your_access_token>`. In Swagger UI, you can use the "Authorize" button to set this token for try-out requests.

*   **Example: Adding a New Camera using `curl` (Linux/macOS)**
    (Replace `<ADMIN_TOKEN>` with your actual token, and adjust camera details.)
    ```bash
    curl -X POST "http://localhost:8000/api/admin/cameras/" \
         -H "Authorization: Bearer <ADMIN_TOKEN>" \
         -H "Content-Type: application/json" \
         -d '{
               "name": "New Office Cam",
               "rtsp_url": "rtsp://user:pass@192.168.1.150/stream1",
               "location": "Main Office Floor",
               "is_active": true
             }'
    ```
    This will create the new camera and its default settings. You should then see it appear in the "NETWORK ASSETS" list in the web dashboard after a refresh or if the list auto-updates.

*   **Other Camera Admin Endpoints:**
    *   `PUT /api/admin/cameras/{camera_id}`: Update a camera's details.
    *   `DELETE /api/admin/cameras/{camera_id}`: Delete a camera and its associated settings/logs.
    Refer to the API documentation (`/docs`) for detailed request body schemas and parameters for these endpoints.

### 6.3. (Placeholder: User Management via API/UI - if implemented)
*(User Guide Note: User management beyond the initial admin user (e.g., creating non-admin users, changing passwords through UI) is a planned future enhancement.)*

---

## 7. Troubleshooting

This section covers common issues you might encounter and how to resolve them.

*   **Server Startup Errors:**
    *   **`uvicorn: command not found` (or similar for `alembic`, `pip`):**
        *   **Cause:** Your Python virtual environment (`venv`) is likely not activated in your current terminal session, or Python/pip is not correctly installed/in PATH.
        *   **Solution:** Ensure you activate the virtual environment (`source venv/bin/activate` or `venv\Scripts\activate.bat`) before running scripts or `pip install`. Verify Python and pip installation.
    *   **Port `8000` already in use (e.g., `Address already in use`):**
        *   **Cause:** Another application is using port 8000.
        *   **Solution:** Stop the other application, or configure CamKord to use a different port by editing the `uvicorn` command in `start_backend.sh`/`.bat` (e.g., change `--port 8000` to `--port 8001`). Remember to update `CORS_ALLOWED_ORIGINS` and the URL you use in your browser accordingly.
    *   **Errors related to missing Environment Variables (e.g., `SECRET_KEY`):**
        *   **Cause:** Critical environment variables like `SECRET_KEY` were not set (or left as placeholders) in the startup script.
        *   **Solution:** Edit `start_backend.sh` or `start_backend.bat` and ensure `SECRET_KEY` (and `DATA_ENCRYPTION_KEY` if using snapshot encryption) are properly set with generated values as per the "Installation & Setup" section.
    *   **Python errors on startup (shows a traceback):**
        *   **Cause:** Could be missing dependencies, incorrect Python version, or code issues.
        *   **Solution:** Ensure all dependencies are installed (`pip install -r requirements.txt`). Check your Python version against requirements. Review the traceback for specific error messages.

*   **Web Dashboard Issues:**
    *   **Dashboard not loading (e.g., "This site can’t be reached"):**
        *   **Cause:** CamKord server is not running, or you're using the wrong URL.
        *   **Solution:** Ensure the backend server is started successfully. Check the URL (`http://localhost:8000/`). Check for firewall issues if accessing from another machine.
    *   **CORS Errors (in browser console):**
        *   **Cause:** The `CORS_ALLOWED_ORIGINS` environment variable is not correctly configured for the URL you are using to access the frontend.
        *   **Solution:** Update `CORS_ALLOWED_ORIGINS` in your startup script to include the origin of your frontend access.
    *   **"Authentication failed" on login:**
        *   **Cause:** Incorrect username or password. Remember the default username is `admin`.
        *   **Solution:** Double-check credentials. Ensure `CAMERA_SUITE_ADMIN_PASS` was set correctly in the startup script when the admin user was first created.
    *   **Video feed not showing / WebSocket errors (check browser console):**
        *   **Cause:** WebSocket connection failed (backend not running, network issue, firewall), authentication token issue for WebSocket, incorrect camera RTSP URL, camera offline, or `is_active` flag for camera set to false.
        *   **Solution:** Check server logs for errors related to the specific camera or WebSocket connections. Verify camera RTSP URL and network. Check browser console for WebSocket error messages.
    *   **Cyberpunk theme looks plain or fonts are wrong:**
        *   **Cause:** Custom font files (`BlenderProBook.woff2`, `Oxanium.woff2`, `Cyberpunk.otf`) are missing from the `CamCord/v1/frontend/fonts/` directory.
        *   **Solution:** Ensure you have obtained these font files and placed them in the correct directory as per setup instructions.
    *   **Object detection not working / no overlays:**
        *   **Cause:** YOLO model files (`.cfg`, `.weights`, `.names`) are missing from `CamCord/v1/app/models/`, or the feature is disabled in camera settings.
        *   **Solution:** Place the correct model files in the directory. Enable "Object Detection" in the Camera Configuration panel for the selected camera. Check server logs for errors from `ObjectDetector`.

*   **Database & Migration Issues:**
    *   **Errors running `alembic` commands:**
        *   **Cause:** Not in the correct directory (`CamCord/v1/app/`), virtual environment not active, or `DATABASE_URL` misconfigured.
        *   **Solution:** Ensure you `cd CamCord/v1/app/` before running `alembic`. Activate venv. Verify `DATABASE_URL` in `app/config.py` (via environment variable) is correct.
    *   **"Table already exists" or similar during `alembic upgrade head` on an existing DB:**
        *   **Cause:** Trying to create tables that are already there, possibly because `init_db()` created them and Alembic isn't aware.
        *   **Solution:** If starting fresh with Alembic on an existing DB schema that matches your models, you might need to `alembic stamp head` to tell Alembic the DB is up-to-date, then manage future changes with new migrations.

*   **Interpreting Server Logs:**
    *   The CamKord server (Uvicorn and FastAPI) prints log messages to the console where you ran the startup script.
    *   Look for lines containing `INFO`, `WARNING`, or `ERROR`. Errors often include a "traceback" showing where in the Python code the problem occurred.
    *   CamKord-specific logs are prefixed (e.g., `[CameraManager]`, `[ManagedCamera X]`, `[WS Auth]`).

---

## 8. Security Best Practices (Summary)

While detailed security advice is in `README.md` under "Security Considerations," here are vital reminders:

*   **Always use HTTPS in production:** Deploy behind a reverse proxy that handles SSL/TLS.
*   **Protect your `SECRET_KEY`, `DATA_ENCRYPTION_KEY`, and `CAMERA_SUITE_ADMIN_PASS`:** Use strong, unique values and keep them confidential. Do not commit them to version control.
*   **Keep Software Updated:** Regularly update CamKord (if it becomes a versioned project), Python dependencies (`requirements.txt`), and your server's operating system.
*   **Network Security:** Use firewalls and run CamKord in a trusted network environment.
*   **Review `README.md`:** For a more comprehensive list of security recommendations.

```
