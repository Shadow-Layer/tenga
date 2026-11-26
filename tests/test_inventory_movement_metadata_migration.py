import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.dialects import postgresql

from src.models.entities import InventoryMovement


ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_REVISION = "till_cash_control_v001"


def migration_config(database_url: str) -> Config:
    config = Config()
    config.set_main_option("sqlalchemy.url", database_url)
    config.set_main_option("script_location", str(ROOT / "src" / "migrations"))
    return config


def run_migration(config: Config, database_url: str, revision: str) -> None:
    original = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        command.upgrade(config, revision)
    finally:
        if original is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original


def run_downgrade(config: Config, database_url: str, revision: str) -> None:
    original = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        command.downgrade(config, revision)
    finally:
        if original is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original


def get_movement_columns(engine):
    return {
        column["name"]: column
        for column in inspect(engine).get_columns("inventory_movement")
    }


def test_fresh_sqlite_upgrade_adds_nullable_inventory_metadata():
    db_path = ROOT / "tests" / ".inventory-metadata-fresh.sqlite"
    db_path.unlink(missing_ok=True)
    database_url = f"sqlite:///{db_path}"
    engine = create_engine(database_url)
    config = migration_config(database_url)
    try:
        run_migration(config, database_url, "inventory_operation_notes_v001")
        columns = get_movement_columns(engine)
        assert columns["notes"]["nullable"] is True
        assert columns["external_reference"]["nullable"] is True

        run_migration(config, database_url, "inventory_operation_notes_v001")
        assert {"notes", "external_reference"} <= set(get_movement_columns(engine))
    finally:
        engine.dispose()
        db_path.unlink(missing_ok=True)


def test_upgrade_is_safe_when_one_metadata_column_already_exists():
    db_path = ROOT / "tests" / ".inventory-metadata-partial.sqlite"
    db_path.unlink(missing_ok=True)
    database_url = f"sqlite:///{db_path}"
    engine = create_engine(database_url)
    config = migration_config(database_url)
    try:
        run_migration(config, database_url, PREVIOUS_REVISION)
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE inventory_movement ADD COLUMN notes TEXT")
            )

        run_migration(config, database_url, "inventory_operation_notes_v001")
        columns = get_movement_columns(engine)
        assert columns["notes"]["nullable"] is True
        assert columns["external_reference"]["nullable"] is True
    finally:
        engine.dispose()
        db_path.unlink(missing_ok=True)


def test_legacy_sqlite_upgrade_preserves_movements_and_refuses_lossy_downgrade():
    db_path = ROOT / "tests" / ".inventory-metadata-legacy.sqlite"
    db_path.unlink(missing_ok=True)
    database_url = f"sqlite:///{db_path}"
    engine = create_engine(database_url)
    config = migration_config(database_url)
    try:
        run_migration(config, database_url, PREVIOUS_REVISION)
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO inventory_movement "
                    "(id, organization_id, location_id, product_id, movement_type, "
                    "quantity, reason, recorded_by_id, created_at) "
                    "VALUES (1, 10, 20, 30, 'ADJUSTMENT', 4, 'LEGACY', 40, "
                    "'2026-01-01 00:00:00')"
                )
            )

        run_migration(config, database_url, "inventory_operation_notes_v001")
        with engine.begin() as connection:
            assert connection.execute(
                text(
                    "SELECT quantity, notes, external_reference "
                    "FROM inventory_movement WHERE id = 1"
                )
            ).one() == (4, None, None)
            connection.execute(
                text(
                    "UPDATE inventory_movement "
                    "SET notes = 'counted at close', external_reference = 'COUNT-17' "
                    "WHERE id = 1"
                )
            )

        try:
            run_downgrade(config, database_url, PREVIOUS_REVISION)
        except RuntimeError as error:
            assert "refusing a destructive downgrade" in str(error)
        else:
            raise AssertionError("Downgrade discarded inventory operation metadata")

        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE inventory_movement "
                    "SET notes = NULL, external_reference = NULL WHERE id = 1"
                )
            )
        run_downgrade(config, database_url, PREVIOUS_REVISION)
        assert not {"notes", "external_reference"} & set(get_movement_columns(engine))

        run_migration(config, database_url, "inventory_operation_notes_v001")
        with engine.begin() as connection:
            assert connection.execute(
                text(
                    "SELECT quantity, notes, external_reference "
                    "FROM inventory_movement WHERE id = 1"
                )
            ).one() == (4, None, None)
    finally:
        engine.dispose()
        db_path.unlink(missing_ok=True)


def test_inventory_metadata_types_compile_for_postgresql():
    columns = InventoryMovement.__table__.c
    assert columns.notes.nullable
    assert columns.external_reference.nullable
    assert columns.notes.type.compile(dialect=postgresql.dialect()) == "TEXT"
    assert (
        columns.external_reference.type.compile(dialect=postgresql.dialect())
        == "VARCHAR(255)"
    )
