"""Add operational, inventory, payment and offline foundation entities.

Revision ID: production_foundation_v001
Revises: setup_imports_v001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "production_foundation_v001"
down_revision: Union[str, Sequence[str], None] = "setup_imports_v001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("organization", sa.Column("phone", sa.String(50), nullable=True))
    op.add_column("organization", sa.Column("email", sa.String(255), nullable=True))
    op.add_column("organization", sa.Column("address", sa.Text(), nullable=True))
    op.add_column("organization", sa.Column("region", sa.String(100), nullable=True))
    op.add_column(
        "organization",
        sa.Column("timezone", sa.String(100), nullable=False, server_default="UTC"),
    )
    op.add_column("organization", sa.Column("currency_code", sa.String(3), nullable=True))

    op.create_table(
        "employee",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("employee_number", sa.String(50), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("title", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.UniqueConstraint("organization_id", "employee_number", name="uq_employee_org_number"),
        sa.UniqueConstraint("user_id", name="uq_employee_user"),
    )
    op.create_index(
        "ix_employee_organization_active", "employee", ["organization_id", "is_active"]
    )

    op.create_table(
        "employee_location_assignment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employee.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["location.id"]),
        sa.UniqueConstraint("employee_id", "location_id", name="uq_employee_location"),
    )
    op.create_table(
        "employee_till_assignment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("till_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employee.id"]),
        sa.ForeignKeyConstraint(["till_id"], ["till.id"]),
        sa.UniqueConstraint("employee_id", "till_id", name="uq_employee_till"),
    )

    op.add_column(
        "product",
        sa.Column("unit_of_measure", sa.String(50), nullable=False, server_default="each"),
    )
    op.add_column(
        "product",
        sa.Column("minimum_stock_level", sa.Integer(), nullable=False, server_default="0"),
    )

    op.add_column("inventory_movement", sa.Column("to_location_id", sa.Integer(), nullable=True))
    op.add_column(
        "inventory_movement",
        sa.Column("recorded_by_employee_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "inventory_movement",
        sa.Column("unit_cost", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.add_column("inventory_movement", sa.Column("currency_code", sa.String(3), nullable=True))
    op.add_column("inventory_movement", sa.Column("device_id", sa.String(100), nullable=True))
    op.add_column(
        "inventory_movement", sa.Column("device_local_id", sa.String(100), nullable=True)
    )
    with op.batch_alter_table("inventory_movement") as batch_op:
        batch_op.create_foreign_key(
            "fk_inventory_movement_destination_location",
            "location",
            ["to_location_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_inventory_movement_employee",
            "employee",
            ["recorded_by_employee_id"],
            ["id"],
        )
        batch_op.create_unique_constraint(
            "uq_inventory_movement_device_operation",
            ["organization_id", "device_id", "device_local_id"],
        )

    op.add_column("sale", sa.Column("location_id", sa.Integer(), nullable=True))
    op.add_column("sale", sa.Column("currency_code", sa.String(3), nullable=True))
    op.add_column("sale", sa.Column("fiscal_number", sa.String(50), nullable=True))
    op.add_column(
        "sale",
        sa.Column("fiscal_status", sa.String(20), nullable=False, server_default="pending"),
    )
    op.add_column("sale", sa.Column("fiscal_status_updated_at", sa.DateTime(), nullable=True))
    op.add_column(
        "sale",
        sa.Column("fiscal_submission_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    with op.batch_alter_table("sale") as batch_op:
        batch_op.create_foreign_key(
            "fk_sale_till_session", "till_session", ["till_session_id"], ["id"]
        )
        batch_op.create_foreign_key("fk_sale_location", "location", ["location_id"], ["id"])
        batch_op.create_unique_constraint("uq_sale_fiscal_number", ["fiscal_number"])

    op.add_column(
        "till_session",
        sa.Column("expected_closing_balance", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.add_column(
        "till_session", sa.Column("cash_variance", sa.Numeric(precision=12, scale=2), nullable=True)
    )
    op.add_column("till_session", sa.Column("currency_code", sa.String(3), nullable=True))
    op.add_column("till_session", sa.Column("closed_by_id", sa.Integer(), nullable=True))
    with op.batch_alter_table("till_session") as batch_op:
        batch_op.create_foreign_key(
            "fk_till_session_closed_by", "user", ["closed_by_id"], ["id"]
        )

    op.create_table(
        "payment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("sale_id", sa.Integer(), nullable=False),
        sa.Column("payment_method", sa.String(30), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "amount_tendered",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "change_given",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),
        sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="COMPLETED"),
        sa.Column("provider_reference", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"]),
        sa.ForeignKeyConstraint(["sale_id"], ["sale.id"]),
    )
    op.create_index("ix_payment_organization_created", "payment", ["organization_id", "created_at"])

    op.create_table(
        "payment_attempt",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("sale_id", sa.Integer(), nullable=False),
        sa.Column("till_session_id", sa.Integer(), nullable=False),
        sa.Column("initiated_by_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("payment_method", sa.String(30), nullable=False),
        sa.Column("merchant_reference", sa.String(100), nullable=False),
        sa.Column("provider_reference", sa.String(255), nullable=True),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("redirect_url", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"]),
        sa.ForeignKeyConstraint(["sale_id"], ["sale.id"]),
        sa.ForeignKeyConstraint(["till_session_id"], ["till_session.id"]),
        sa.ForeignKeyConstraint(["initiated_by_id"], ["user.id"]),
        sa.UniqueConstraint(
            "organization_id", "merchant_reference", name="uq_payment_attempt_merchant_ref"
        ),
        sa.UniqueConstraint("provider_reference", name="uq_payment_attempt_provider_ref"),
    )
    op.create_index(
        "ix_payment_attempt_org_status", "payment_attempt", ["organization_id", "status"]
    )

    op.create_table(
        "fiscal_submission",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("sale_id", sa.Integer(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("request_reference", sa.String(100), nullable=False),
        sa.Column("fiscal_number", sa.String(100), nullable=True),
        sa.Column("request_payload", sa.Text(), nullable=True),
        sa.Column("response_payload", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"]),
        sa.ForeignKeyConstraint(["sale_id"], ["sale.id"]),
        sa.UniqueConstraint("sale_id", "attempt_number", name="uq_fiscal_submission_attempt"),
    )
    op.create_index(
        "ix_fiscal_submission_org_status", "fiscal_submission", ["organization_id", "status"]
    )

    op.create_table(
        "receipt_audit",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("sale_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"]),
        sa.ForeignKeyConstraint(["sale_id"], ["sale.id"]),
        sa.ForeignKeyConstraint(["actor_id"], ["user.id"]),
    )

    op.create_table(
        "offline_operation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.String(100), nullable=False),
        sa.Column("operation_id", sa.String(100), nullable=False),
        sa.Column("operation_type", sa.String(30), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("result_payload", sa.Text(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"]),
        sa.ForeignKeyConstraint(["actor_id"], ["user.id"]),
        sa.UniqueConstraint(
            "organization_id", "device_id", "operation_id", name="uq_offline_operation_identity"
        ),
    )
    op.create_index("ix_offline_operation_org_status", "offline_operation", ["organization_id", "status"])

    op.create_table(
        "inventory_count",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("reconciled_by_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("reconciled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["location.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["reconciled_by_id"], ["user.id"]),
    )
    op.create_index(
        "ix_inventory_count_org_status", "inventory_count", ["organization_id", "status"]
    )
    op.create_table(
        "inventory_count_line",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("count_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("expected_quantity", sa.Integer(), nullable=False),
        sa.Column("observed_quantity", sa.Integer(), nullable=True),
        sa.Column("reconciled_movement_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["count_id"], ["inventory_count.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
        sa.ForeignKeyConstraint(["reconciled_movement_id"], ["inventory_movement.id"]),
        sa.UniqueConstraint("count_id", "product_id", name="uq_inventory_count_product"),
    )

    op.create_table(
        "inventory_transfer",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("source_location_id", sa.Integer(), nullable=False),
        sa.Column("destination_location_id", sa.Integer(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.String(100), nullable=True),
        sa.Column("device_local_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="COMPLETED"),
        sa.Column("reason", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"]),
        sa.ForeignKeyConstraint(["source_location_id"], ["location.id"]),
        sa.ForeignKeyConstraint(["destination_location_id"], ["location.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["user.id"]),
        sa.UniqueConstraint(
            "organization_id",
            "device_id",
            "device_local_id",
            name="uq_inventory_transfer_device_operation",
        ),
    )
    op.create_table(
        "inventory_transfer_line",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("transfer_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["transfer_id"], ["inventory_transfer.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
    )


def downgrade() -> None:
    op.drop_table("inventory_transfer_line")
    op.drop_table("inventory_transfer")
    op.drop_table("inventory_count_line")
    op.drop_index("ix_inventory_count_org_status", table_name="inventory_count")
    op.drop_table("inventory_count")
    op.drop_index("ix_offline_operation_org_status", table_name="offline_operation")
    op.drop_table("offline_operation")
    op.drop_table("receipt_audit")
    op.drop_index("ix_fiscal_submission_org_status", table_name="fiscal_submission")
    op.drop_table("fiscal_submission")
    op.drop_index("ix_payment_attempt_org_status", table_name="payment_attempt")
    op.drop_table("payment_attempt")
    op.drop_index("ix_payment_organization_created", table_name="payment")
    op.drop_table("payment")
    with op.batch_alter_table("till_session") as batch_op:
        batch_op.drop_constraint("fk_till_session_closed_by", type_="foreignkey")
        batch_op.drop_column("closed_by_id")
        batch_op.drop_column("currency_code")
        batch_op.drop_column("cash_variance")
        batch_op.drop_column("expected_closing_balance")
    with op.batch_alter_table("sale") as batch_op:
        batch_op.drop_constraint("uq_sale_fiscal_number", type_="unique")
        batch_op.drop_constraint("fk_sale_location", type_="foreignkey")
        batch_op.drop_constraint("fk_sale_till_session", type_="foreignkey")
        batch_op.drop_column("fiscal_submission_attempts")
        batch_op.drop_column("fiscal_status_updated_at")
        batch_op.drop_column("fiscal_status")
        batch_op.drop_column("fiscal_number")
        batch_op.drop_column("currency_code")
        batch_op.drop_column("location_id")
    with op.batch_alter_table("inventory_movement") as batch_op:
        batch_op.drop_constraint("uq_inventory_movement_device_operation", type_="unique")
        batch_op.drop_constraint(
            "fk_inventory_movement_employee", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_inventory_movement_destination_location", type_="foreignkey"
        )
        batch_op.drop_column("device_local_id")
        batch_op.drop_column("device_id")
        batch_op.drop_column("currency_code")
        batch_op.drop_column("unit_cost")
        batch_op.drop_column("recorded_by_employee_id")
        batch_op.drop_column("to_location_id")
    op.drop_column("product", "minimum_stock_level")
    op.drop_column("product", "unit_of_measure")
    op.drop_table("employee_till_assignment")
    op.drop_table("employee_location_assignment")
    op.drop_index("ix_employee_organization_active", table_name="employee")
    op.drop_table("employee")
    op.drop_column("organization", "currency_code")
    op.drop_column("organization", "timezone")
    op.drop_column("organization", "region")
    op.drop_column("organization", "address")
    op.drop_column("organization", "email")
    op.drop_column("organization", "phone")
