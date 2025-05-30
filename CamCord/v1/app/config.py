config.py

""" Centralized configuration module using Pydantic for environment-driven settings. """ from pydantic import BaseSettings, Field from typing import List

class Settings(BaseSettings): # Server settings SERVER_HOST: str = Field("0.0.0.0", env="SERVER_HOST") SERVER_PORT: int = Field(8000, env="SERVER_PORT") DEBUG: bool = Field(False, env="DEBUG")

# Camera settings
CAMERA_INDEX: int = Field(0, env="CAMERA_INDEX")
DEFAULT_RESOLUTION: str = Field("1280x720", env="DEFAULT_RESOLUTION")
SUPPORTED_RESOLUTIONS: List[str] = Field(["640x480", "1280x720", "1920x1080"], env="SUPPORTED_RESOLUTIONS")

# Database settings
DATABASE_URL: str = Field("sqlite:///./data/camera_suite.db", env="DATABASE_URL")

# Authentication settings
# For production, SECRET_KEY must be set to a strong random string via environment variables.
# It is critical for securing user sessions and sensitive data.
SECRET_KEY: str = Field(..., env="SECRET_KEY") # Made mandatory by using ...
ALGORITHM: str = Field("HS256", env="ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(60, env="ACCESS_TOKEN_EXPIRE_MINUTES")

# Directories
SNAPSHOT_DIR: str = Field("snapshots", env="SNAPSHOT_DIR")
RECORDING_DIR: str = Field("recordings", env="RECORDING_DIR")
LOG_DIR: str = Field("logs", env="LOG_DIR")

# CORS settings
# Comma-separated list of allowed origins for CORS. E.g., "https://yourdomain.com,https://www.yourdomain.com"
CORS_ALLOWED_ORIGINS: List[str] = Field(default=["http://localhost:3000"], env="CORS_ALLOWED_ORIGINS")

    # For encrypting/decrypting snapshots.
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # Store this key securely as an environment variable.
    DATA_ENCRYPTION_KEY: Optional[str] = Field(default=None, env="DATA_ENCRYPTION_KEY")

class Config:
    env_file = ".env"
    case_sensitive = True

Instantiate a single settings object for import

settings = Settings()
