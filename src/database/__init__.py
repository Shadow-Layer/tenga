"""Database initialization and session management."""
from src.database.config import Base, engine, SessionLocal, init_db, drop_db

__all__ = ["Base", "engine", "SessionLocal", "init_db", "drop_db"]


def create_all_tables() -> None:
    """Create all tables in the database."""
    if engine is None:
        raise RuntimeError("Database engine not configured.")
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
