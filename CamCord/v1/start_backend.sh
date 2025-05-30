#!/bin/bash
echo "Starting CamKord Backend..."
echo "--------------------------------------------------"
echo "IMPORTANT: Please edit this script to set your environment variables."
echo "--------------------------------------------------"

# --- Configuration ---
# A strong, random string for SECRET_KEY is crucial for security.
# Generate one using: openssl rand -hex 32
export SECRET_KEY="!!!REPLACE_WITH_YOUR_STRONG_RANDOM_KEY!!!"

# Set this to define the initial admin password (username will be 'admin').
# If left as "!!!REPLACE...", the default admin user will NOT be created.
export CAMERA_SUITE_ADMIN_PASS="!!!REPLACE_WITH_YOUR_ADMIN_PASSWORD!!!"

# Configure allowed origins for CORS (comma-separated list for the app to parse).
# If FastAPI serves the frontend (current setup), allowing its own origin is typical.
export CORS_ALLOWED_ORIGINS="http://localhost:8000,http://127.0.0.1:8000"
# For production, replace with your actual frontend domain(s) if served separately:
# export CORS_ALLOWED_ORIGINS="https://your.frontend.domain.com"

# Optional: Define a non-default database URL (defaults to sqlite in app/data/camera_suite.db)
# export DATABASE_URL="sqlite:///./data/production_camkord.db"

echo ""
echo "Using Configuration:"
echo "SECRET_KEY: ${SECRET_KEY:0:5}... (partially hidden for security)" 
if [ "$CAMERA_SUITE_ADMIN_PASS" = "!!!REPLACE_WITH_YOUR_ADMIN_PASSWORD!!!" ]; then
    echo "CAMERA_SUITE_ADMIN_PASS: Not set (default admin will not be created)"
else
    echo "CAMERA_SUITE_ADMIN_PASS: Set (admin user 'admin' will be created/updated)"
fi
echo "CORS_ALLOWED_ORIGINS: ${CORS_ALLOWED_ORIGINS}"
echo "DATABASE_URL: ${DATABASE_URL:-Using default SQLite in app/data/}"
echo "--------------------------------------------------"
echo "--- Starting Uvicorn Server ---"

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Change to the 'app' directory (where main.py is located)
cd "${SCRIPT_DIR}/app" || { echo "Error: Failed to change to 'app' directory from ${SCRIPT_DIR}. Ensure 'app' is a subdirectory."; exit 1; }

# Start Uvicorn server for main:app (main.py, app = FastAPI instance)
# Remove --reload for a production-like setup. Add for active development.
uvicorn main:app --host 0.0.0.0 --port 8000

echo "--------------------------------------------------"
echo "CamKord Backend stopped."
