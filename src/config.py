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
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() == "true"
CORS_ALLOW_METHODS = ["*"]
CORS_ALLOW_HEADERS = ["*"]

# JWT/Authentication settings
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 8 hours
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Ensure secrets are configured in production
if ENVIRONMENT == Environment.PROD:
    if JWT_SECRET_KEY == "dev-secret-key-change-in-production":
        raise ValueError(
            "JWT_SECRET_KEY must be configured in production environment. "
            "Set JWT_SECRET_KEY environment variable."
        )
