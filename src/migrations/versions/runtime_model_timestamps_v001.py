"""Backfill common timestamps required by operational ORM models.

Revision ID: runtime_model_timestamps_v001
Revises: sync_protocol_v001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "runtime_model_timestamps_v001"
down_revision: Union[str, Sequence[str], None] = "sync_protocol_v001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TIMESTAMP_COLUMNS = {
    "stock": ("created_at", "updated_at"),
    "inventory_movement": ("updated_at",),
    "sale_item": ("created_at", "updated_at"),
}
_TRACKING_TABLE = "runtime_model_timestamp_migration_columns"


def _column_metadata() -> dict[str, dict[str, dict]]:
    inspector = sa.inspect(op.get_bind())
    return {
        table: {column["name"]: column for column in inspector.get_columns(table)}
        for table in _TIMESTAMP_COLUMNS
    }


def upgrade() -> None:
    columns = _column_metadata()
    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())
    if _TRACKING_TABLE not in existing_tables:
        op.create_table(
            _TRACKING_TABLE,
            sa.Column("table_name", sa.String(100), nullable=False),
            sa.Column("column_name", sa.String(100), nullable=False),
            sa.Column("column_added", sa.Boolean(), nullable=False),
            sa.Column("original_nullable", sa.Boolean(), nullable=True),
            sa.PrimaryKeyConstraint("table_name", "column_name"),
        )

    added_columns = set()
    for table, names in _TIMESTAMP_COLUMNS.items():
        if not columns[table]:
            raise RuntimeError(f"Cannot add runtime timestamps: {table} table is missing.")
        for name in names:
            if name not in columns[table]:
                op.add_column(table, sa.Column(name, sa.DateTime(), nullable=True))
                added_columns.add((table, name))
                op.get_bind().execute(
                    sa.text(
                        f"INSERT INTO {_TRACKING_TABLE} "
                        "(table_name, column_name, column_added, original_nullable) "
                        "VALUES (:table_name, :column_name, true, NULL)"
                    ),
                    {"table_name": table, "column_name": name},
                )

    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE stock SET created_at = COALESCE(last_movement_at, CURRENT_TIMESTAMP) "
            "WHERE created_at IS NULL"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE stock SET updated_at = COALESCE(last_movement_at, created_at, CURRENT_TIMESTAMP) "
            "WHERE updated_at IS NULL"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE inventory_movement SET updated_at = created_at WHERE updated_at IS NULL"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE sale_item SET created_at = COALESCE("
            "(SELECT sale.created_at FROM sale WHERE sale.id = sale_item.sale_id), "
            "CURRENT_TIMESTAMP) WHERE created_at IS NULL"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE sale_item SET updated_at = created_at WHERE updated_at IS NULL"
        )
    )

    columns = _column_metadata()
    for table, names in _TIMESTAMP_COLUMNS.items():
        nullable = [name for name in names if columns[table][name]["nullable"]]
        if nullable:
            for name in nullable:
                if (table, name) not in added_columns:
                    bind.execute(
                        sa.text(
                            f"INSERT INTO {_TRACKING_TABLE} "
                            "(table_name, column_name, column_added, original_nullable) "
                            "VALUES (:table_name, :column_name, false, true)"
                        ),
                        {"table_name": table, "column_name": name},
                    )
            with op.batch_alter_table(table) as batch_op:
                for name in nullable:
                    batch_op.alter_column(
                        name,
                        existing_type=sa.DateTime(),
                        nullable=False,
                    )


def downgrade() -> None:
    bind = op.get_bind()
    if _TRACKING_TABLE not in sa.inspect(bind).get_table_names():
        return

    added_columns = bind.execute(
        sa.text(
            f"SELECT table_name, column_name, column_added, original_nullable "
            f"FROM {_TRACKING_TABLE} "
            "ORDER BY table_name, column_name"
        )
    ).all()
    added = [row for row in added_columns if row.column_added]
    for table in {row.table_name for row in added}:
        if bind.execute(sa.text(f'SELECT 1 FROM "{table}" LIMIT 1')).first():
            raise RuntimeError(
                f"{table} contains operational records; refusing a destructive downgrade that would remove timestamp columns."
            )

    for table in reversed(tuple(_TIMESTAMP_COLUMNS)):
        nullable = [
            row.column_name
            for row in added_columns
            if row.table_name == table and bool(row.original_nullable)
        ]
        if nullable:
            with op.batch_alter_table(table) as batch_op:
                for name in nullable:
                    batch_op.alter_column(
                        name,
                        existing_type=sa.DateTime(),
                        nullable=True,
                    )

        names = [
            row.column_name
            for row in added
            if row.table_name == table
        ]
        if names:
            with op.batch_alter_table(table) as batch_op:
                for name in reversed(names):
                    batch_op.drop_column(name)
    op.drop_table(_TRACKING_TABLE)
