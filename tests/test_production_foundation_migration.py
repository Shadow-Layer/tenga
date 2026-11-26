import os
import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, inspect, text


ROOT = Path(__file__).resolve().parents[1]


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


def test_upgrade_preserves_legacy_rows_and_does_not_assign_currency():
    with tempfile.TemporaryDirectory(prefix="tenga-foundation-migration-") as directory:
        db_path = Path(directory) / "legacy.sqlite"
        database_url = f"sqlite:///{db_path}"
        engine = create_engine(database_url)
        config = migration_config(database_url)

        run_migration(config, database_url, "setup_imports_v001")
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO organization "
                    "(id, name, code, is_active, created_at, updated_at) "
                    "VALUES (1, 'Legacy', 'LEGACY', 1, '2026-01-01', '2026-01-01')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO user "
                    "(id, organization_id, email, username, password_hash, role, "
                    "is_active, created_at, updated_at) "
                    "VALUES (1, 1, 'owner@example.test', 'owner', 'hash', 'admin', "
                    "1, '2026-01-01', '2026-01-01')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO location "
                    "(id, organization_id, code, name, is_active, created_at, updated_at) "
                    "VALUES (1, 1, 'MAIN', 'Main', 1, '2026-01-01', '2026-01-01')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO product "
                    "(id, organization_id, sku, name, price, cost, is_active, created_at, updated_at) "
                    "VALUES (1, 1, 'SKU-1', 'Item', 10, 4, 1, '2026-01-01', '2026-01-01')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO till "
                    "(id, organization_id, location_id, code, name, is_active, created_at, updated_at) "
                    "VALUES (1, 1, 1, 'T1', 'Till 1', 1, '2026-01-01', '2026-01-01')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO sale "
                    "(id, organization_id, till_id, cashier_id, total_amount, discount_amount, "
                    "tax_amount, payment_method, status, till_session_id, source_type, "
                    "created_at, updated_at) "
                    "VALUES (1, 1, 1, 1, 10, 0, 0, 'cash', 'completed', NULL, "
                    "'LIVE', '2026-01-01', '2026-01-01')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO stock "
                    "(id, organization_id, location_id, product_id, quantity, last_movement_at) "
                    "VALUES (1, 1, 1, 1, 12, '2026-01-02')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO inventory_movement "
                    "(id, organization_id, location_id, product_id, movement_type, quantity, "
                    "reason, reference_id, reference_type, recorded_by_id, created_at) "
                    "VALUES (1, 1, 1, 1, 'RECEIPT', 12, 'RECEIPT', NULL, NULL, 1, '2026-01-03')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO sale_item "
                    "(id, sale_id, product_id, quantity, unit_price, discount_per_item, total_price) "
                    "VALUES (1, 1, 1, 1, 10, 0, 10)"
                )
            )

        run_migration(config, database_url, "head")

        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT currency_code FROM organization WHERE id = 1")
            ).scalar_one() is None
            assert connection.execute(
                text("SELECT unit_of_measure FROM product WHERE id = 1")
            ).scalar_one() == "each"
            assert connection.execute(
                text("SELECT minimum_stock_level FROM product WHERE id = 1")
            ).scalar_one() == 0
            assert connection.execute(
                text("SELECT total_amount FROM sale WHERE id = 1")
            ).scalar_one() == 10
            assert connection.execute(
                text("SELECT till_session_id FROM sale WHERE id = 1")
            ).scalar_one() is None
            assert connection.execute(
                text("SELECT fiscal_status FROM sale WHERE id = 1")
            ).scalar_one() == "pending"
            assert connection.execute(
                text("SELECT created_at, updated_at FROM stock WHERE id = 1")
            ).one() == ("2026-01-02", "2026-01-02")
            assert connection.execute(
                text("SELECT created_at, updated_at FROM inventory_movement WHERE id = 1")
            ).one() == ("2026-01-03", "2026-01-03")
            assert connection.execute(
                text("SELECT created_at, updated_at FROM sale_item WHERE id = 1")
            ).one() == ("2026-01-01", "2026-01-01")

        inspector = inspect(engine)
        assert {
            "employee",
            "payment_attempt",
            "offline_operation",
            "inventory_count",
            "till_cash_movement",
        } <= set(
            inspector.get_table_names()
        )
        assignment_columns = {
            column["name"]
            for column in inspector.get_columns("employee_location_assignment")
        }
        assert "ended_at" in assignment_columns
        assignment_indexes = {
            index["name"]: index
            for index in inspector.get_indexes("employee_location_assignment")
        }
        assert bool(assignment_indexes["uq_employee_location_active"]["unique"])
        session_indexes = {
            index["name"]: index for index in inspector.get_indexes("till_session")
        }
        assert bool(session_indexes["uq_till_session_one_open_per_till"]["unique"])
        sale_foreign_keys = {
            tuple(foreign_key["constrained_columns"])
            for foreign_key in inspector.get_foreign_keys("sale")
        }
        assert ("till_session_id",) in sale_foreign_keys
        engine.dispose()


def test_sync_protocol_migration_creates_all_runtime_sync_tables():
    with tempfile.TemporaryDirectory(prefix="tenga-sync-migration-") as directory:
        db_path = Path(directory) / "fresh.sqlite"
        database_url = f"sqlite:///{db_path}"
        engine = create_engine(database_url)
        config = migration_config(database_url)

        run_migration(config, database_url, "head")

        inspector = inspect(engine)
        assert {
            "cached_subscription_state",
            "sync_logs",
            "sync_batch_transactions",
            "device_sync_caches",
            "sync_idempotency_caches",
        } <= set(inspector.get_table_names())
        timestamp_columns = {
            "stock": {"created_at", "updated_at"},
            "inventory_movement": {"created_at", "updated_at"},
            "sale_item": {"created_at", "updated_at"},
        }
        for table, expected in timestamp_columns.items():
            columns = {
                column["name"]: column
                for column in inspector.get_columns(table)
            }
            assert expected <= set(columns)
            assert all(not columns[name]["nullable"] for name in expected)

        cache_indexes = {
            index["name"]: index
            for index in inspector.get_indexes("cached_subscription_state")
        }
        assert cache_indexes["ix_cached_subscription_state_device_id"]["unique"]
        log_indexes = {
            index["name"] for index in inspector.get_indexes("sync_logs")
        }
        assert {
            "ix_sync_logs_batch_id",
            "ix_sync_logs_device_id",
            "ix_sync_logs_timestamp",
        } <= log_indexes
        engine.dispose()


def test_timestamp_downgrade_preserves_columns_that_predated_migration():
    with tempfile.TemporaryDirectory(prefix="tenga-timestamp-downgrade-") as directory:
        db_path = Path(directory) / "legacy.sqlite"
        database_url = f"sqlite:///{db_path}"
        engine = create_engine(database_url)
        config = migration_config(database_url)

        run_migration(config, database_url, "sync_protocol_v001")
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE stock ADD COLUMN created_at DATETIME"))

        run_migration(config, database_url, "head")
        upgraded_columns = {
            column["name"]: column
            for column in inspect(engine).get_columns("stock")
        }
        assert not upgraded_columns["created_at"]["nullable"]
        run_downgrade(config, database_url, "sync_protocol_v001")

        inspector = inspect(engine)
        stock_columns = {
            column["name"]: column for column in inspector.get_columns("stock")
        }
        assert "created_at" in stock_columns
        assert "updated_at" not in stock_columns
        assert stock_columns["created_at"]["nullable"]
        assert "runtime_model_timestamp_migration_columns" not in inspector.get_table_names()
        engine.dispose()


def test_till_control_migration_refuses_duplicate_open_sessions():
    with tempfile.TemporaryDirectory(prefix="tenga-open-session-migration-") as directory:
        db_path = Path(directory) / "legacy.sqlite"
        database_url = f"sqlite:///{db_path}"
        engine = create_engine(database_url)
        config = migration_config(database_url)
        run_migration(config, database_url, "employee_assignment_history_v001")

        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO organization "
                    "(id, name, code, is_active, timezone, created_at, updated_at) "
                    "VALUES (1, 'Legacy', 'LEGACY', 1, 'UTC', '2026-01-01', '2026-01-01')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO user "
                    "(id, organization_id, email, username, password_hash, role, "
                    "is_active, created_at, updated_at) "
                    "VALUES (1, 1, 'owner@example.test', 'owner', 'hash', 'admin', "
                    "1, '2026-01-01', '2026-01-01')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO location "
                    "(id, organization_id, code, name, is_active, created_at, updated_at) "
                    "VALUES (1, 1, 'MAIN', 'Main', 1, '2026-01-01', '2026-01-01')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO till "
                    "(id, organization_id, location_id, code, name, is_active, created_at, updated_at) "
                    "VALUES (1, 1, 1, 'T1', 'Till 1', 1, '2026-01-01', '2026-01-01')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO till_session "
                    "(id, organization_id, till_id, operator_id, session_number, "
                    "opening_balance, status, opened_at, created_at, updated_at) "
                    "VALUES "
                    "(1, 1, 1, 1, 'S1', 0, 'OPEN', '2026-01-01', '2026-01-01', '2026-01-01'), "
                    "(2, 1, 1, 1, 'S2', 0, 'open', '2026-01-02', '2026-01-02', '2026-01-02')"
                )
            )

        with pytest.raises(RuntimeError, match="duplicate open sessions"):
            run_migration(config, database_url, "head")

        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == "employee_assignment_history_v001"
        engine.dispose()
