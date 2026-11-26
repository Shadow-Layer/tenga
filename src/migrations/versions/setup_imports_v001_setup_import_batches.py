"""Add import audit records and imported-sale identity fields.

Revision ID: setup_imports_v001
Revises: tax_rules_v001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "setup_imports_v001"
down_revision: Union[str, Sequence[str], None] = "tax_rules_v001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "data_import_batch",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("import_type", sa.String(length=30), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["user.id"]),
        sa.UniqueConstraint(
            "organization_id",
            "import_type",
            "content_sha256",
            name="uq_data_import_org_type_hash",
        ),
    )
    op.create_index(
        "ix_data_import_organization_created",
        "data_import_batch",
        ["organization_id", "created_at"],
    )
    with op.batch_alter_table("sale") as batch_op:
        batch_op.add_column(
            sa.Column(
                "source_type",
                sa.String(length=30),
                nullable=False,
                server_default="LIVE",
            )
        )
        batch_op.add_column(sa.Column("external_reference", sa.String(length=255)))
        batch_op.create_unique_constraint(
            "uq_sale_org_external_reference",
            ["organization_id", "external_reference"],
        )


def downgrade() -> None:
    with op.batch_alter_table("sale") as batch_op:
        batch_op.drop_constraint("uq_sale_org_external_reference", type_="unique")
        batch_op.drop_column("external_reference")
        batch_op.drop_column("source_type")
    op.drop_index("ix_data_import_organization_created", table_name="data_import_batch")
    op.drop_table("data_import_batch")
