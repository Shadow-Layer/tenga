"""Database configuration and initialization."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

# Base for all ORM models
Base = declarative_base()

# Default database path (SQLite for MVP)
DB_PATH = os.getenv("DATABASE_URL", "sqlite:////home/tea/Documents/apps/tenga-inventory/tenga.db")

# Create engine with SQLite-specific settings
engine = create_engine(
    DB_PATH,
    connect_args={"check_same_thread": False} if "sqlite" in DB_PATH else {},
    poolclass=StaticPool if "sqlite" in DB_PATH else None,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database schema."""
    Base.metadata.create_all(bind=engine)


def drop_db():
    """Drop all tables (for testing)."""
    Base.metadata.drop_all(bind=engine)
