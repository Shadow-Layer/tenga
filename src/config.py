"""Application configuration management."""
import os
from enum import Enum


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
API_VERSION = "T008"

# Database URL configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////data/tenga.db")

# SQL Echo (verbose logging)
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true"

# CORS settings
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() == "true"
CORS_ALLOW_METHODS = ["*"]
CORS_ALLOW_HEADERS = ["*"]
