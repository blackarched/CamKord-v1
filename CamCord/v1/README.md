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

### Database Migrations (Alembic)

This project uses [Alembic](https://alembic.sqlalchemy.org/) to manage database schema migrations. This allows your database schema to evolve along with changes to the application's SQLAlchemy models (defined in `app/database.py`).

**Initial Database Setup with Alembic:**

If you are setting up the project for the first time, or connecting to a new empty database:

1.  **Configure `DATABASE_URL`:** Ensure your `DATABASE_URL` (in your startup script or environment) points to your target database.
2.  **Navigate to the `app` directory:** All Alembic commands should typically be run from the `CamCord/v1/app/` directory, as this is where `alembic.ini` is located.
    ```bash
    cd CamCord/v1/app  # Or your equivalent path to the 'app' directory
    ```
3.  **Stamp the database with the latest revision (if models already match initial migration):**
    If an initial migration script representing all current tables already exists in `app/alembic/versions/` (e.g., from previous setup or by another developer), and your database is currently empty but you want it to be set up *as if* all migrations up to 'head' have run, you can "stamp" it:
    ```bash
    alembic stamp head
    ```
    Then, the `init_db()` function called on application startup (from `app/main.py`) will create all tables based on the current models. Stamping prevents Alembic from trying to run old migrations on a DB that `init_db()` will fully create.
    Alternatively, if you want Alembic to create the tables from an initial migration script:

4.  **Generating an Initial Migration (if no migration script exists yet for current models):**
    If there are no migration scripts in `app/alembic/versions/` or if you want to generate one from scratch based on current models:
    ```bash
    alembic revision -m "Create initial database schema based on current models" --autogenerate
    ```
    *   This command compares the models defined in `app.database.Base.metadata` with the target database (if any tables exist) and generates a new script in `app/alembic/versions/`.
    *   **Important:** Always open and review the generated script. Alembic's autogenerate is powerful but might not capture every nuance perfectly, especially for complex constraints or custom types. You may need to edit the script.

5.  **Apply Migrations to Create Schema:**
    To apply all migrations (or the initial one you just generated) to your database, creating all tables:
    ```bash
    alembic upgrade head
    ```
    This will bring your database schema to the state defined by the latest migration script. (Note: The `init_db()` function in `app/main.py` also calls `Base.metadata.create_all(engine)`, which creates tables if they don't exist. For a new setup, either `init_db()` or `alembic upgrade head` can create the tables. Using Alembic from the start is good practice for schema versioning.)

**Managing Schema Changes (After Initial Setup):**

Whenever you modify your SQLAlchemy models in `app/database.py` (e.g., add a new table, add/remove a column):

1.  **Navigate to `CamCord/v1/app/`**.
2.  **Generate a new migration script:**
    ```bash
    alembic revision -m "Your concise description of model changes (e.g., add_email_to_users_table)" --autogenerate
    ```
3.  **Review and edit the generated script** in `app/alembic/versions/` for correctness and completeness.
4.  **Apply the migration to your database:**
    ```bash
    alembic upgrade head
    ```

**Other Useful Alembic Commands (from `CamCord/v1/app/`):**

*   `alembic current`: Show the current revision of the database.
*   `alembic history`: Show the migration history.
*   `alembic downgrade -1`: Downgrade by one revision.
*   `alembic downgrade <revision_id>`: Downgrade to a specific revision.
*   `alembic upgrade <revision_id>`: Upgrade to a specific revision.

Using Alembic consistently ensures your database schema is version-controlled and can be reliably updated alongside your application code.

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

## Security Considerations

Ensuring the security of your CamKord deployment is critical, especially as it handles video feeds and potentially sensitive data. Please consider the following:

### HTTPS/SSL/TLS
For any production deployment, it is **strongly recommended** to run CamKord behind a reverse proxy (e.g., Nginx, Traefik, Caddy) that handles SSL/TLS termination. This ensures that all communication between clients (browsers, mobile apps) and the CamKord server is encrypted via HTTPS.
*   Uvicorn, when run directly as in the startup scripts, serves HTTP. This is suitable for local development or within a trusted network where the reverse proxy handles external HTTPS.
*   Obtain SSL certificates for your domain, for example, using Let's Encrypt (often integrated with reverse proxies).

### Important Security Headers
Configure your reverse proxy to add essential HTTP security headers to client responses. These headers help protect against common web vulnerabilities:
*   `Strict-Transport-Security (HSTS)`: Instructs browsers to only communicate with the server over HTTPS. Example: `Strict-Transport-Security: max-age=31536000; includeSubDomains`
*   `X-Content-Type-Options: nosniff`: Prevents browsers from MIME-sniffing the content-type, reducing risk of XSS.
*   `X-Frame-Options: DENY` or `SAMEORIGIN`: Protects against clickjacking attacks by controlling how your site can be embedded in iframes.
*   `Content-Security-Policy (CSP)`: A powerful header to control resources the browser is allowed to load, mitigating XSS and data injection attacks. CSP can be complex to configure correctly but offers significant protection. Example (very restrictive): `Content-Security-Policy: default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self';` (Needs careful tuning for your specific frontend needs, especially if using CDNs or inline scripts/styles extensively).

### Environment Variables & Secrets
*   **`SECRET_KEY`**: This is used for signing JWTs and other security functions. It **must** be a long, random, and unique string, kept confidential, and set in your startup script (or system environment). Do not commit your actual secret key to version control.
*   **`CAMERA_SUITE_ADMIN_PASS`**: Set a strong, unique password for the initial 'admin' user via this environment variable in your startup script.
*   **`DATA_ENCRYPTION_KEY`**: (If snapshot/recording encryption is fully implemented) This key, if used for encrypting data at rest, must also be kept highly confidential and secure.

### API Rate Limiting
The application includes rate limiting on critical API endpoints (like login) to help protect against brute-force attacks and denial-of-service attempts. Default limits are set, but review them if you have specific needs.

### Database Security
*   The default SQLite database (`app/data/camera_suite.db`) stores application data, including user credentials (hashed passwords) and event logs. Ensure this file and its directory are protected with appropriate file system permissions to restrict access.
*   For more robust security, scalability, and management features in a larger production environment, consider migrating to a dedicated database server like PostgreSQL.

### Storage for Snapshots and Recordings
*   Snapshots are encrypted at rest if the `DATA_ENCRYPTION_KEY` is configured and encryption logic is active. (Verify current status of this feature).
*   Video recordings are currently saved as standard MP4 files and are **not** encrypted at rest by the application itself.
*   Protect the storage directories for snapshots (`app/snapshots/`) and recordings (`app/recordings/`) with strong file system permissions.
*   Consider full-disk encryption on the server for an additional layer of protection for all data at rest.

### Regular Software Updates
Keep all dependencies listed in `requirements.txt` (especially FastAPI, Uvicorn, cryptography libraries) and the underlying system software (OS, Python) up to date to ensure you have the latest security patches.

### Network Security
*   Run CamKord within a trusted network environment.
*   If exposing to the internet (even via reverse proxy), ensure your firewall is properly configured to only allow necessary ports (e.g., 443 for HTTPS).

### Physical Security
*   Ensure the server running CamKord and the cameras themselves are physically secure to prevent unauthorized access or tampering.

## Docker Deployment (Recommended)

This application can be easily deployed using Docker. A `Dockerfile` is provided.

**1. Prerequisites:**
*   Docker installed and running.

**2. Prepare Files (Important):**
    *   **Environment Variables:** While the Dockerfile sets some defaults, critical secrets like `SECRET_KEY`, `DATA_ENCRYPTION_KEY`, and `CAMERA_SUITE_ADMIN_PASS` **must not be hardcoded in the Dockerfile with production values**. Pass them during `docker run` using the `-e` flag or via `docker-compose.yml`.
    *   **Font Files:** Place required font files (`BlenderProBook.woff2`, `Oxanium.woff2`, `Cyberpunk.otf`) into the `CamCord/v1/frontend/fonts/` directory on your host machine if you intend to build them into the image. Alternatively, mount this as a volume.
    *   **Object Detection Models:** Place model files (`yolov4-tiny.cfg`, `yolov4-tiny.weights`, `coco.names`) into `CamCord/v1/app/models/` on your host if building into the image. Alternatively, mount as a volume.

**3. Build the Docker Image:**
Navigate to the `CamCord/v1/` directory (where the `Dockerfile` is located) and run:
```bash
docker build -t camkord-app .
```

**4. Run the Docker Container:**
Here's an example `docker run` command. Adjust paths and environment variables as needed.

```bash
docker run -d --name camkord-instance \
    -p 8000:8000 \
    -e SECRET_KEY="YOUR_VERY_STRONG_SECRET_KEY_HERE" \
    -e DATA_ENCRYPTION_KEY="YOUR_GENERATED_FERNET_KEY_HERE" \
    -e CAMERA_SUITE_ADMIN_PASS="YourSecureAdminP@ssw0rd" \
    -e CORS_ALLOWED_ORIGINS="http://your.frontend.domain:port,https://your.other.domain" \
    -e DATABASE_URL="sqlite:///data/camera_suite.db" \
    -v $(pwd)/app/data:/opt/camkord/app/data \
    -v $(pwd)/app/models:/opt/camkord/app/models \
    -v $(pwd)/app/recordings:/opt/camkord/app/recordings \
    -v $(pwd)/app/snapshots:/opt/camkord/app/snapshots \
    -v $(pwd)/frontend/fonts:/opt/camkord/frontend/fonts \
    camkord-app
```
**Explanation of `docker run` options:**
*   `-d`: Run in detached mode (background).
*   `--name camkord-instance`: Assign a name to the container.
*   `-p 8000:8000`: Map port 8000 of the host to port 8000 in the container.
*   `-e VARIABLE="value"`: Set environment variables. **Crucially, set `SECRET_KEY`, `DATA_ENCRYPTION_KEY`, and `CAMERA_SUITE_ADMIN_PASS` here.**
*   `-v $(pwd)/host/path:/container/path`: Mount volumes for persistent data.
    *   `app/data`: For the SQLite database.
    *   `app/models`: For YOLO model files (if not copied into image during build).
    *   `app/recordings`: For video recordings.
    *   `app/snapshots`: For snapshots.
    *   `frontend/fonts`: For font files (if not copied into image).
    Adjust `$(pwd)` (or use absolute paths) based on where you run the command.

**5. Accessing the Application:**
Once the container is running, access the application at `http://localhost:8000` (or your server's IP/domain if deployed remotely).

**6. Viewing Logs:**
```bash
docker logs camkord-instance
```

**7. Stopping the Container:**
```bash
docker stop camkord-instance
```
