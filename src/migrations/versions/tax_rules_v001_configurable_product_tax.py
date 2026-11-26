"""Add configurable organization tax rules and sale-line tax snapshots.

Revision ID: tax_rules_v001
Revises: add_barcode_v001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "tax_rules_v001"
down_revision: Union[str, Sequence[str], None] = "add_barcode_v001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tax_rule",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("rate", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("tax_inclusive", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("rate >= 0 AND rate <= 100", name="ck_tax_rule_rate_range"),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"]),
        sa.UniqueConstraint("organization_id", "name", name="uq_tax_rule_org_name"),
    )
    op.create_index(
        "ix_tax_rule_organization_active",
        "tax_rule",
        ["organization_id", "is_active"],
    )
    with op.batch_alter_table("product") as batch_op:
        batch_op.add_column(sa.Column("tax_rule_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_product_tax_rule_id_tax_rule",
            "tax_rule",
            ["tax_rule_id"],
            ["id"],
        )
    op.add_column("sale_item", sa.Column("tax_rule_id", sa.Integer(), nullable=True))
    op.add_column(
        "sale_item",
        sa.Column(
            "tax_rate",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "sale",
        sa.Column(
            "amount_tendered",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "sale",
        sa.Column(
            "change_given",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "sale_item",
        sa.Column(
            "tax_inclusive",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "sale_item",
        sa.Column(
            "tax_amount",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("sale", "change_given")
    op.drop_column("sale", "amount_tendered")
    op.drop_column("sale_item", "tax_amount")
    op.drop_column("sale_item", "tax_inclusive")
    op.drop_column("sale_item", "tax_rate")
    op.drop_column("sale_item", "tax_rule_id")
    with op.batch_alter_table("product") as batch_op:
        batch_op.drop_constraint("fk_product_tax_rule_id_tax_rule", type_="foreignkey")
        batch_op.drop_column("tax_rule_id")
    op.drop_index("ix_tax_rule_organization_active", table_name="tax_rule")
    op.drop_table("tax_rule")
