"""Preserve employee assignment history when access is revoked.

Revision ID: employee_assignment_history_v001
Revises: production_foundation_v001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "employee_assignment_history_v001"
down_revision: Union[str, Sequence[str], None] = "production_foundation_v001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("employee_location_assignment") as batch:
        batch.add_column(sa.Column("ended_at", sa.DateTime(), nullable=True))
        batch.drop_constraint("uq_employee_location", type_="unique")
    with op.batch_alter_table("employee_till_assignment") as batch:
        batch.add_column(sa.Column("ended_at", sa.DateTime(), nullable=True))
        batch.drop_constraint("uq_employee_till", type_="unique")

    predicate = sa.text("ended_at IS NULL")
    op.create_index(
        "uq_employee_location_active",
        "employee_location_assignment",
        ["employee_id", "location_id"],
        unique=True,
        sqlite_where=predicate,
        postgresql_where=predicate,
    )
    op.create_index(
        "uq_employee_till_active",
        "employee_till_assignment",
        ["employee_id", "till_id"],
        unique=True,
        sqlite_where=predicate,
        postgresql_where=predicate,
    )


def downgrade() -> None:
    connection = op.get_bind()
    for table_name in (
        "employee_location_assignment",
        "employee_till_assignment",
    ):
        if connection.execute(
            sa.text(f"SELECT 1 FROM {table_name} WHERE ended_at IS NOT NULL LIMIT 1")
        ).first():
            raise RuntimeError(
                "Employee assignment history exists; refusing a destructive downgrade."
            )

    op.drop_index(
        "uq_employee_location_active", table_name="employee_location_assignment"
    )
    op.drop_index("uq_employee_till_active", table_name="employee_till_assignment")
    with op.batch_alter_table("employee_location_assignment") as batch:
        batch.drop_column("ended_at")
        batch.create_unique_constraint(
            "uq_employee_location", ["employee_id", "location_id"]
        )
    with op.batch_alter_table("employee_till_assignment") as batch:
        batch.drop_column("ended_at")
        batch.create_unique_constraint("uq_employee_till", ["employee_id", "till_id"])
