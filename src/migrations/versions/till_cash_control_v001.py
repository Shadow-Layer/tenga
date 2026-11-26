"""Persist till cash movements and enforce one open session per till.

Revision ID: till_cash_control_v001
Revises: employee_assignment_history_v001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "till_cash_control_v001"
down_revision: Union[str, Sequence[str], None] = "employee_assignment_history_v001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    duplicates = connection.execute(
        sa.text(
            "SELECT organization_id, till_id, COUNT(*) "
            "FROM till_session WHERE upper(status) = 'OPEN' "
            "GROUP BY organization_id, till_id HAVING COUNT(*) > 1"
        )
    ).all()
    if duplicates:
        raise RuntimeError(
            "Cannot enforce one open session per till: duplicate open sessions exist. "
            "Reconcile and close duplicate sessions before retrying this migration."
        )

    op.create_index(
        "uq_till_session_one_open_per_till",
        "till_session",
        ["till_id"],
        unique=True,
        sqlite_where=sa.text("upper(status) = 'OPEN'"),
        postgresql_where=sa.text("upper(status) = 'OPEN'"),
    )
    op.create_table(
        "till_cash_movement",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("till_id", sa.Integer(), nullable=False),
        sa.Column("till_session_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=True),
        sa.Column("operation_id", sa.String(100), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("reference", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"]),
        sa.ForeignKeyConstraint(["till_id"], ["till.id"]),
        sa.ForeignKeyConstraint(["till_session_id"], ["till_session.id"]),
        sa.ForeignKeyConstraint(["actor_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employee.id"]),
        sa.UniqueConstraint(
            "organization_id",
            "operation_id",
            name="uq_till_cash_movement_operation",
        ),
        sa.CheckConstraint("amount > 0", name="ck_till_cash_movement_positive_amount"),
        sa.CheckConstraint(
            "direction IN ('CASH_IN', 'CASH_OUT')",
            name="ck_till_cash_movement_direction",
        ),
    )
    op.create_index(
        "ix_till_cash_movement_session_created",
        "till_cash_movement",
        ["organization_id", "till_session_id", "created_at"],
    )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.execute(
        sa.text("SELECT 1 FROM till_cash_movement LIMIT 1")
    ).first():
        raise RuntimeError(
            "Till cash movement history exists; refusing a destructive downgrade."
        )
    op.drop_index(
        "ix_till_cash_movement_session_created",
        table_name="till_cash_movement",
    )
    op.drop_table("till_cash_movement")
    op.drop_index(
        "uq_till_session_one_open_per_till",
        table_name="till_session",
    )
