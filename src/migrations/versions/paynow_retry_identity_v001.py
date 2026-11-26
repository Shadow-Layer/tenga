"""Persist Paynow retry identity and prevent duplicate child attempts.

Revision ID: paynow_retry_identity_v001
Revises: inventory_operation_notes_v001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "paynow_retry_identity_v001"
down_revision: Union[str, Sequence[str], None] = "inventory_operation_notes_v001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("payment_attempt") as batch_op:
        batch_op.add_column(
            sa.Column("retry_of_attempt_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_payment_attempt_retry_parent",
            "payment_attempt",
            ["retry_of_attempt_id"],
            ["id"],
        )
    op.create_index(
        "uq_payment_attempt_retry_parent",
        "payment_attempt",
        ["retry_of_attempt_id"],
        unique=True,
    )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.execute(
        sa.text(
            "SELECT 1 FROM payment_attempt "
            "WHERE retry_of_attempt_id IS NOT NULL LIMIT 1"
        )
    ).first():
        raise RuntimeError(
            "Paynow retry history exists; refusing to remove retry identity."
        )
    op.drop_index(
        "uq_payment_attempt_retry_parent",
        table_name="payment_attempt",
    )
    with op.batch_alter_table("payment_attempt") as batch_op:
        batch_op.drop_constraint(
            "fk_payment_attempt_retry_parent",
            type_="foreignkey",
        )
        batch_op.drop_column("retry_of_attempt_id")
