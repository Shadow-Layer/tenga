"""Database migration utilities and version management."""
import os
import json
from pathlib import Path
from datetime import datetime
from sqlalchemy import text
from src.database.config import engine, Base

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
SCHEMA_VERSION_FILE = MIGRATIONS_DIR / ".schema_version"


def get_schema_version() -> str:
    """Get current schema version."""
    if SCHEMA_VERSION_FILE.exists():
        with open(SCHEMA_VERSION_FILE, "r") as f:
            return f.read().strip()
    return "0"


def set_schema_version(version: str) -> None:
    """Set current schema version."""
    MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)
    with open(SCHEMA_VERSION_FILE, "w") as f:
        f.write(version)


def create_migration_entry() -> None:
    """Record migration application timestamp."""
    MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)
    
    migration_log = {
        "timestamp": datetime.utcnow().isoformat(),
        "schema_version": "v001",
        "description": "Initial schema creation - Foundation T001"
    }
    
    log_file = MIGRATIONS_DIR / f"v001_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, "w") as f:
        json.dump(migration_log, f, indent=2)


def apply_migrations() -> None:
    """Apply all pending migrations."""
    current_version = get_schema_version()
    
    if current_version == "0":
        print("Applying v001: Initial schema creation...")
        Base.metadata.create_all(bind=engine)
        set_schema_version("v001")
        create_migration_entry()
        print("✓ Schema v001 applied successfully")
    else:
        print(f"Schema already at version {current_version}")


def rollback_schema() -> None:
    """Drop all tables (use with caution - testing only)."""
    print("WARNING: Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    set_schema_version("0")
    print("✓ Schema rolled back")
