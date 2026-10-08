"""Database configuration and initialization."""
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool, NullPool

# Base for all ORM models
Base = declarative_base()

# Database URL configuration
# For development/testing: SQLite (default)
# For production: PostgreSQL
# Examples:
#   sqlite:///:memory:  (in-memory for tests)
#   sqlite:///path/to/tenga.db  (file-based)
#   postgresql://user:password@host:5432/tenga  (PostgreSQL)
def get_database_url() -> str:
    """Build database URL from environment variables."""
    env = os.getenv("ENVIRONMENT", "dev")
    
    # Check for explicit DATABASE_URL first
    if "DATABASE_URL" in os.environ:
        return os.environ["DATABASE_URL"]
    
    # For production, require PostgreSQL configuration
    if env == "prod":
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "tenga")
        user = os.getenv("POSTGRES_USER", "tenga_user")
        password = os.getenv("POSTGRES_PASSWORD")
        
        if not password:
            raise ValueError("POSTGRES_PASSWORD must be set in production")
        
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"
    
    # Default to SQLite for dev/test
    db_path = os.getenv("SQLITE_PATH", "/data/tenga.db")
    return f"sqlite:///{db_path}"

DB_URL = get_database_url()

# Detect database type
IS_SQLITE = "sqlite" in DB_URL
IS_POSTGRESQL = "postgresql" in DB_URL

# Engine configuration based on database type
engine_kwargs = {
    "echo": os.getenv("SQL_ECHO", "false").lower() == "true",
}

if IS_SQLITE:
    # SQLite-specific settings
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine_kwargs["poolclass"] = StaticPool
elif IS_POSTGRESQL:
    # PostgreSQL-specific settings
    engine_kwargs["pool_size"] = int(os.getenv("DB_POOL_SIZE", "10"))
    engine_kwargs["max_overflow"] = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    engine_kwargs["pool_pre_ping"] = True  # Verify connections before using
    engine_kwargs["pool_recycle"] = 3600  # Recycle connections after 1 hour
else:
    # Default pool settings for other databases
    engine_kwargs["poolclass"] = NullPool

# Create engine
engine = create_engine(DB_URL, **engine_kwargs)

# Enable SQLite foreign keys if using SQLite
if IS_SQLITE:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Enable SQLite foreign key constraints."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

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
