"""Create durable synchronization and subscription-cache tables.

Revision ID: sync_protocol_v001
Revises: paynow_retry_identity_v001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "sync_protocol_v001"
down_revision: Union[str, Sequence[str], None] = "paynow_retry_identity_v001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _enum_type(*values: str, name: str):
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        enum_type = postgresql.ENUM(*values, name=name, create_type=False)
        enum_type.create(bind, checkfirst=True)
        return enum_type
    return sa.Enum(*values, name=name, native_enum=False)


def upgrade() -> None:
    sync_status = _enum_type(
        "SUCCESS", "PARTIAL_FAILURE", "DUPLICATE", "FAILED", name="syncstatus"
    )
    transaction_type = _enum_type("SALE", "MOVEMENT", name="transactiontype")
    transaction_status = _enum_type(
        "PENDING", "APPLIED", "FAILED", name="transactionstatus"
    )
    subscription_state = _enum_type(
        "ACTIVE", "GRACE", "EXPIRED", name="subscriptionstate"
    )

    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "cached_subscription_state" not in tables:
        op.create_table(
            "cached_subscription_state",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("device_id", sa.String(100), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("state", sa.String(20), nullable=False),
            sa.Column("state_snapshot", sa.JSON(), nullable=False),
            sa.Column("last_sync_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organization.id"]),
        )
        op.create_index(
            "ix_cached_subscription_state_device_id",
            "cached_subscription_state",
            ["device_id"],
            unique=True,
        )
        op.create_index(
            "ix_cached_subscription_state_organization_id",
            "cached_subscription_state",
            ["organization_id"],
        )

    if "sync_logs" not in tables:
        op.create_table(
            "sync_logs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("device_id", sa.String(100), nullable=False),
            sa.Column("batch_id", sa.String(100), nullable=False),
            sa.Column("batch_size", sa.Integer(), nullable=False),
            sa.Column("status", sync_status, nullable=False),
            sa.Column("timestamp", sa.DateTime(), nullable=False),
            sa.Column("organization_id", sa.String(36), nullable=True),
            sa.Column("cached_response_json", sa.JSON(), nullable=True),
            sa.Column("sync_duration_ms", sa.Integer(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
        )
        op.create_index("ix_sync_logs_device_id", "sync_logs", ["device_id"])
        op.create_index("ix_sync_logs_batch_id", "sync_logs", ["batch_id"])
        op.create_index("ix_sync_logs_timestamp", "sync_logs", ["timestamp"])

    if "sync_batch_transactions" not in tables:
        op.create_table(
            "sync_batch_transactions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("sync_log_id", sa.String(36), nullable=False),
            sa.Column("transaction_sequence", sa.Integer(), nullable=False),
            sa.Column("transaction_type", transaction_type, nullable=False),
            sa.Column("status", transaction_status, nullable=False),
            sa.Column("transaction_data", sa.JSON(), nullable=False),
            sa.Column("applied_at", sa.DateTime(), nullable=True),
            sa.Column("failure_reason", sa.Text(), nullable=True),
            sa.Column("applied_entity_id", sa.String(36), nullable=True),
            sa.Column("applied_entity_type", sa.String(50), nullable=True),
            sa.ForeignKeyConstraint(["sync_log_id"], ["sync_logs.id"]),
        )
        op.create_index(
            "ix_sync_batch_transactions_sync_log_id",
            "sync_batch_transactions",
            ["sync_log_id"],
        )

    if "device_sync_caches" not in tables:
        op.create_table(
            "device_sync_caches",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("device_id", sa.String(100), nullable=False),
            sa.Column("last_synced_at", sa.DateTime(), nullable=True),
            sa.Column("last_sync_log_id", sa.String(36), nullable=True),
            sa.Column("cached_subscription_state", subscription_state, nullable=True),
            sa.Column("cached_state_expires_at", sa.DateTime(), nullable=True),
            sa.Column("device_name", sa.String(255), nullable=True),
            sa.Column("last_device_timestamp", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["last_sync_log_id"], ["sync_logs.id"]),
        )
        op.create_index(
            "ix_device_sync_caches_device_id",
            "device_sync_caches",
            ["device_id"],
            unique=True,
        )

    if "sync_idempotency_caches" not in tables:
        op.create_table(
            "sync_idempotency_caches",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("device_id", sa.String(100), nullable=False),
            sa.Column("batch_id", sa.String(100), nullable=False),
            sa.Column("sync_log_id", sa.String(36), nullable=False),
            sa.Column("response_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["sync_log_id"], ["sync_logs.id"]),
            sa.UniqueConstraint("device_id", "batch_id", name="uq_device_batch"),
        )
        for column in ("device_id", "batch_id", "created_at", "expires_at"):
            op.create_index(
                f"ix_sync_idempotency_caches_{column}",
                "sync_idempotency_caches",
                [column],
            )


def downgrade() -> None:
    connection = op.get_bind()
    table_order = (
        "sync_idempotency_caches",
        "device_sync_caches",
        "sync_batch_transactions",
        "sync_logs",
        "cached_subscription_state",
    )
    existing = set(sa.inspect(connection).get_table_names())
    for table in table_order:
        if table in existing and connection.execute(
            sa.text(f'SELECT 1 FROM "{table}" LIMIT 1')
        ).first():
            raise RuntimeError(
                f"{table} contains synchronization history; refusing to remove it."
            )

    for table in table_order:
        if table in existing:
            op.drop_table(table)

    if connection.dialect.name == "postgresql":
        for enum_name in (
            "subscriptionstate",
            "transactionstatus",
            "transactiontype",
            "syncstatus",
        ):
            postgresql.ENUM(name=enum_name).drop(connection, checkfirst=True)
