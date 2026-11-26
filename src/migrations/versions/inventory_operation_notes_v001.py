"""Persist notes and external references on inventory movements.

Revision ID: inventory_operation_notes_v001
Revises: till_cash_control_v001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "inventory_operation_notes_v001"
down_revision: Union[str, Sequence[str], None] = "till_cash_control_v001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_COLUMNS = {
    "notes": sa.Column("notes", sa.Text(), nullable=True),
    "external_reference": sa.Column("external_reference", sa.String(255), nullable=True),
}


def _existing_columns() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if "inventory_movement" not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns("inventory_movement")}


def upgrade() -> None:
    existing = _existing_columns()
    if not existing:
        raise RuntimeError("Cannot add inventory metadata: inventory_movement table is missing.")

    for name, column in _COLUMNS.items():
        if name not in existing:
            op.add_column("inventory_movement", column)


def downgrade() -> None:
    existing = _existing_columns()
    if not existing:
        return

    present_metadata = existing.intersection(_COLUMNS)
    if present_metadata:
        predicates = [f"{name} IS NOT NULL" for name in sorted(present_metadata)]
        populated = op.get_bind().execute(
            sa.text(
                "SELECT 1 FROM inventory_movement WHERE "
                + " OR ".join(predicates)
                + " LIMIT 1"
            )
        ).first()
        if populated:
            raise RuntimeError(
                "Inventory movement notes or external references exist; "
                "refusing a destructive downgrade."
            )

    for name in reversed(tuple(_COLUMNS)):
        if name in existing:
            op.drop_column("inventory_movement", name)
