# Start with an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /opt/camkord

# Set environment variables for Python (improves stability and logging)
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# --- Application Environment Variables ---
# These are defaults. Critical secrets (SECRET_KEY, DATA_ENCRYPTION_KEY, CAMERA_SUITE_ADMIN_PASS)
# MUST be overridden at runtime for security (e.g., via docker run -e or docker-compose.yml).
ENV APP_MODULE="app.main:app"
ENV HOST="0.0.0.0"
ENV PORT="8000"

# Default CORS for containerized app. Override if frontend is external or different port.
ENV CORS_ALLOWED_ORIGINS="http://localhost:8000,http://127.0.0.1:8000"

# Default Database URL (SQLite within the container's /opt/camkord/app/data directory)
# For persistent data, this path should be volume-mounted from the host.
ENV DATABASE_URL="sqlite:///./data/camera_suite.db"

# Create necessary directories for data, models, fonts.
# These paths will be relative to WORKDIR /opt/camkord.
# These also serve as placeholders for potential volume mounts.
RUN mkdir -p app/data             && mkdir -p app/models             && mkdir -p app/recordings             && mkdir -p app/snapshots             && mkdir -p app/logs             && mkdir -p frontend/fonts

# Install system dependencies required by OpenCV and other libraries
# libgl1-mesa-glx is for headless OpenCV. ffmpeg for video processing.
RUN apt-get update && apt-get install -y --no-install-recommends             libgl1-mesa-glx             ffmpeg             && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY ./requirements.txt /opt/camkord/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
# Ensure .dockerignore is used if there are files/folders to exclude
COPY ./app /opt/camkord/app
COPY ./frontend /opt/camkord/frontend

# Expose the port the app runs on (defined by ENV PORT)
EXPOSE ${PORT}

# Define the command to run the application
# Use Gunicorn to manage Uvicorn workers.
# Number of workers: (2 * CPU_CORES) + 1 is a common recommendation. Defaulting to 4.
# Timeout: Increased for potentially long-lived streaming connections or processing.
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--timeout", "120", "--bind", "0.0.0.0:${PORT}", "app.main:app"]
