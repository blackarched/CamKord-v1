@echo off
echo Starting CamKord Backend...
echo --------------------------------------------------
echo IMPORTANT: Please edit this script to set your environment variables.
echo --------------------------------------------------

REM --- Configuration ---
REM A strong, random string for SECRET_KEY is crucial for security.
set "SECRET_KEY=!!!REPLACE_WITH_YOUR_STRONG_RANDOM_KEY!!!"

REM Set this to define the initial admin password (username will be 'admin').
REM If left as "!!!REPLACE...", the default admin user will NOT be created.
set "CAMERA_SUITE_ADMIN_PASS=!!!REPLACE_WITH_YOUR_ADMIN_PASSWORD!!!"

REM Configure allowed origins for CORS (comma-separated list for the app to parse).
REM If FastAPI serves the frontend (current setup), allowing its own origin is typical.
set "CORS_ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000"
REM For production, replace with your actual frontend domain(s) if served separately:
REM set "CORS_ALLOWED_ORIGINS=https://your.frontend.domain.com"

REM Optional: Define a non-default database URL (defaults to sqlite in app/data/camera_suite.db)
REM set "DATABASE_URL=sqlite:///./data/production_camkord.db"

echo.
echo Using Configuration:
echo SECRET_KEY: %SECRET_KEY:~0,5%... (partially hidden for security)
if "%CAMERA_SUITE_ADMIN_PASS%"=="!!!REPLACE_WITH_YOUR_ADMIN_PASSWORD!!!" (
    echo CAMERA_SUITE_ADMIN_PASS: Not set (default admin will not be created)
) else (
    echo CAMERA_SUITE_ADMIN_PASS: Set (admin user 'admin' will be created/updated)
)
echo CORS_ALLOWED_ORIGINS: %CORS_ALLOWED_ORIGINS%
if defined DATABASE_URL (
    echo DATABASE_URL: %DATABASE_URL%
) else (
    echo DATABASE_URL: Using default SQLite in app/data/
)
echo --------------------------------------------------
echo --- Starting Uvicorn Server ---

REM Change to the 'app' directory (where main.py is located)
REM %~dp0 expands to the drive and path of the batch script
cd "%~dp0app"
if errorlevel 1 (
    echo Error: Failed to change to 'app' directory from %~dp0. Ensure 'app' is a subdirectory.
    goto :eof
)

REM Start Uvicorn server for main:app (main.py, app = FastAPI instance)
REM Remove --reload for a production-like setup. Add for active development.
uvicorn main:app --host 0.0.0.0 --port 8000

echo --------------------------------------------------
echo CamKord Backend stopped.
:eof
