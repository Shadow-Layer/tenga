"""Application configuration management."""
import os
from enum import Enum
from datetime import timedelta


class Environment(str, Enum):
    """Application environment."""
    DEV = "dev"
    TEST = "test"
    PROD = "prod"


# Environment and settings
ENVIRONMENT = os.getenv("ENVIRONMENT", Environment.DEV)
DEBUG = ENVIRONMENT == Environment.DEV

# API Settings
API_TITLE = "Tenga Inventory POS"
API_DESCRIPTION = "RESTful API for Tenga Inventory Point-of-Sale System"
API_VERSION = "T010"

# Database URL configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////data/tenga.db")

# SQL Echo (verbose logging)
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true"

# CORS settings
CORS_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "CORS_ORIGINS",
        "*" if os.getenv("ENVIRONMENT", "dev") != "prod" else "",
    ).split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() == "true"
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
CORS_ALLOW_HEADERS = ["Authorization", "Content-Type", "X-Setup-Secret"]

# JWT/Authentication settings
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 8 hours
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Initial installation bootstrap is available only when an operator configures
# a high-entropy, single-use deployment secret.
INITIAL_SETUP_SECRET = os.getenv("INITIAL_SETUP_SECRET", "")

# Ensure secrets are configured in production
if ENVIRONMENT == Environment.PROD:
    if len(JWT_SECRET_KEY) < 32 or JWT_SECRET_KEY == "dev-secret-key-change-in-production":
        raise ValueError(
            "JWT_SECRET_KEY must be a non-default secret of at least 32 characters in production."
        )
    if not CORS_ORIGINS or "*" in CORS_ORIGINS:
        raise ValueError("CORS_ORIGINS must contain explicit production origins; wildcard CORS is disabled.")
