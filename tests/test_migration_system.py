"""Tests for database migration system using Alembic."""
import os
import pytest
import tempfile
from pathlib import Path
from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

from src.database.config import Base


class TestAlembicMigrations:
    """Test Alembic migration system."""

    @pytest.fixture
    def migration_db(self):
        """Create a temporary database for migration testing."""
        # Use SQLite for migration tests (simpler setup)
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_migrations.db")
            db_url = f"sqlite:///{db_path}"
            
            engine = create_engine(db_url)
            
            yield engine, db_url
            
            engine.dispose()

    def test_alembic_config_exists(self):
        """Verify Alembic configuration file exists."""
        alembic_ini = Path(__file__).parent.parent / "alembic.ini"
        assert alembic_ini.exists(), "alembic.ini not found"

    def test_migrations_directory_exists(self):
        """Verify migrations directory exists."""
        migrations_dir = Path(__file__).parent.parent / "src" / "migrations"
        assert migrations_dir.exists(), "migrations directory not found"
        assert (migrations_dir / "versions").exists(), "migrations/versions not found"

    def test_migration_files_exist(self):
        """Verify initial migration file exists."""
        versions_dir = Path(__file__).parent.parent / "src" / "migrations" / "versions"
        migration_files = list(versions_dir.glob("*.py"))
        
        # Filter out __pycache__ and __init__
        migration_files = [f for f in migration_files if f.name.endswith('_initial_schema_creation_all_entities.py')]
        
        assert len(migration_files) > 0, "No initial migration file found"

    def test_alembic_env_imports_models(self):
        """Verify Alembic env.py imports our models."""
        env_file = Path(__file__).parent.parent / "src" / "migrations" / "env.py"
        content = env_file.read_text()
        
        assert "from src.database.config import Base" in content, \
            "env.py doesn't import Base"
        assert "target_metadata = Base.metadata" in content, \
            "env.py doesn't set target_metadata"

    def test_migration_upgrade_creates_schema(self, migration_db):
        """Verify upgrade migration creates schema."""
        engine, db_url = migration_db
        
        # Get config
        alembic_cfg = Config()
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        alembic_cfg.set_main_option(
            "script_location",
            str(Path(__file__).parent.parent / "src" / "migrations")
        )
        
        # Run upgrade
        os.environ["DATABASE_URL"] = db_url
        try:
            command.upgrade(alembic_cfg, "head")
        finally:
            del os.environ["DATABASE_URL"]
        
        # Verify tables exist
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        expected_tables = {
            'organization', 'user', 'location', 'product', 'till',
            'subscription', 'stock', 'inventory_movement', 'sale',
            'sale_item', 'till_session'
        }
        
        for table in expected_tables:
            assert table in tables, f"Table {table} not created by migration"

    def test_migration_downgrade_drops_schema(self, migration_db):
        """Verify downgrade migration drops schema."""
        engine, db_url = migration_db
        
        # Get config
        alembic_cfg = Config()
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        alembic_cfg.set_main_option(
            "script_location",
            str(Path(__file__).parent.parent / "src" / "migrations")
        )
        
        # Run upgrade first
        os.environ["DATABASE_URL"] = db_url
        try:
            command.upgrade(alembic_cfg, "head")
            
            # Verify tables exist
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            assert len(tables) > 0, "No tables created by upgrade"
            
            # Now downgrade to base
            command.downgrade(alembic_cfg, "base")
            
            # Verify tables are gone
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            expected_tables = {
                'organization', 'user', 'location', 'product', 'till',
                'subscription', 'stock', 'inventory_movement', 'sale',
                'sale_item', 'till_session'
            }
            
            for table in expected_tables:
                assert table not in tables, f"Table {table} not dropped by downgrade"
        finally:
            del os.environ["DATABASE_URL"]

    def test_migration_tracks_version(self, migration_db):
        """Verify Alembic tracks migration version."""
        engine, db_url = migration_db
        
        # Get config
        alembic_cfg = Config()
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        alembic_cfg.set_main_option(
            "script_location",
            str(Path(__file__).parent.parent / "src" / "migrations")
        )
        
        os.environ["DATABASE_URL"] = db_url
        try:
            # Upgrade
            command.upgrade(alembic_cfg, "head")
            
            # Check alembic_version table exists
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            assert "alembic_version" in tables, "alembic_version table not created"
            
            # Query current version
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                version = result.scalar()
                assert version is not None, "No version recorded"
                assert version == ScriptDirectory.from_config(
                    alembic_cfg
                ).get_current_head(), f"Unexpected version: {version}"
        finally:
            del os.environ["DATABASE_URL"]


class TestMigrationIdempotency:
    """Test that migrations are idempotent."""

    @pytest.fixture
    def migration_db(self):
        """Create a temporary database for migration testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_migrations.db")
            db_url = f"sqlite:///{db_path}"
            
            engine = create_engine(db_url)
            
            yield engine, db_url
            
            engine.dispose()

    def test_upgrade_idempotent(self, migration_db):
        """Verify running upgrade twice is idempotent."""
        engine, db_url = migration_db
        
        alembic_cfg = Config()
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        alembic_cfg.set_main_option(
            "script_location",
            str(Path(__file__).parent.parent / "src" / "migrations")
        )
        
        os.environ["DATABASE_URL"] = db_url
        try:
            # First upgrade
            command.upgrade(alembic_cfg, "head")
            
            inspector1 = inspect(engine)
            tables1 = set(inspector1.get_table_names())
            
            # Second upgrade (should be no-op)
            command.upgrade(alembic_cfg, "head")
            
            inspector2 = inspect(engine)
            tables2 = set(inspector2.get_table_names())
            
            # Should be identical
            assert tables1 == tables2, "Tables changed on second upgrade"
        finally:
            del os.environ["DATABASE_URL"]
