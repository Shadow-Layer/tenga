"""Initial schema creation - all entities

Revision ID: b143c7e5867b
Revises: 
Create Date: 2026-10-08 14:26:57.139701

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b143c7e5867b'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create organization table (no organization_id foreign key for this table)
    op.create_table(
        'organization',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
        sa.UniqueConstraint('name'),
    )
    op.create_index('ix_organization_code', 'organization', ['code'])
    op.create_index('ix_organization_is_active', 'organization', ['is_active'])
    op.create_index('ix_organization_name', 'organization', ['name'])

    # Create user table
    op.create_table(
        'user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organization.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', 'organization_id', name='ix_org_email'),
    )
    op.create_index('ix_user_email', 'user', ['email'])
    op.create_index('ix_user_is_active', 'user', ['is_active'])
    op.create_index('ix_user_organization_id', 'user', ['organization_id'])

    # Create location table
    op.create_table(
        'location',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organization.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', 'organization_id', name='ix_org_code'),
    )
    op.create_index('ix_location_is_active', 'location', ['is_active'])
    op.create_index('ix_location_organization_id', 'location', ['organization_id'])

    # Create product table
    op.create_table(
        'product',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('sku', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('cost', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organization.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sku', 'organization_id', name='ix_org_sku'),
    )
    op.create_index('ix_product_is_active', 'product', ['is_active'])
    op.create_index('ix_product_organization_id', 'product', ['organization_id'])

    # Create till table
    op.create_table(
        'till',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('location_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['location_id'], ['location.id']),
        sa.ForeignKeyConstraint(['organization_id'], ['organization.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', 'organization_id', name='ix_org_code_till'),
    )
    op.create_index('ix_till_is_active', 'till', ['is_active'])
    op.create_index('ix_till_location_id', 'till', ['location_id'])
    op.create_index('ix_till_organization_id', 'till', ['organization_id'])

    # Create subscription table
    op.create_table(
        'subscription',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('plan', sa.String(length=50), nullable=False),
        sa.Column('term', sa.String(length=20), nullable=False),
        sa.Column('state', sa.String(length=50), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('expiry_date', sa.DateTime(), nullable=False),
        sa.Column('grace_end_date', sa.DateTime(), nullable=True),
        sa.Column('auto_renew', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organization.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_subscription_organization_id', 'subscription', ['organization_id'])

    # Create stock table
    op.create_table(
        'stock',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('location_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('last_movement_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['location_id'], ['location.id']),
        sa.ForeignKeyConstraint(['organization_id'], ['organization.id']),
        sa.ForeignKeyConstraint(['product_id'], ['product.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('location_id', 'product_id', name='ix_location_product'),
    )
    op.create_index('ix_stock_organization_id', 'stock', ['organization_id'])

    # Create inventory_movement table (append-only audit trail)
    op.create_table(
        'inventory_movement',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('location_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('movement_type', sa.String(length=20), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(length=100), nullable=False),
        sa.Column('reference_id', sa.Integer(), nullable=True),
        sa.Column('reference_type', sa.String(length=50), nullable=True),
        sa.Column('recorded_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['location_id'], ['location.id']),
        sa.ForeignKeyConstraint(['organization_id'], ['organization.id']),
        sa.ForeignKeyConstraint(['product_id'], ['product.id']),
        sa.ForeignKeyConstraint(['recorded_by_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_inventory_movement_created_at', 'inventory_movement', ['created_at'])
    op.create_index('ix_inventory_movement_location_created', 'inventory_movement', ['location_id', 'created_at'])
    op.create_index('ix_inventory_movement_organization_created', 'inventory_movement', ['organization_id', 'created_at'])
    op.create_index('ix_inventory_movement_product_created', 'inventory_movement', ['product_id', 'created_at'])

    # Create sale table
    op.create_table(
        'sale',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('till_id', sa.Integer(), nullable=False),
        sa.Column('cashier_id', sa.Integer(), nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('discount_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('payment_method', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('till_session_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['cashier_id'], ['user.id']),
        sa.ForeignKeyConstraint(['organization_id'], ['organization.id']),
        sa.ForeignKeyConstraint(['till_id'], ['till.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_sale_created_till', 'sale', ['till_id', 'created_at'])
    op.create_index('ix_sale_organization_created', 'sale', ['organization_id', 'created_at'])

    # Create sale_item table
    op.create_table(
        'sale_item',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sale_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('discount_per_item', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('total_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['product.id']),
        sa.ForeignKeyConstraint(['sale_id'], ['sale.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_sale_item_sale_id', 'sale_item', ['sale_id'])

    # Create till_session table
    op.create_table(
        'till_session',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('till_id', sa.Integer(), nullable=False),
        sa.Column('operator_id', sa.Integer(), nullable=False),
        sa.Column('session_number', sa.String(length=100), nullable=False),
        sa.Column('opening_balance', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('closing_balance', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('opened_at', sa.DateTime(), nullable=False),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['operator_id'], ['user.id']),
        sa.ForeignKeyConstraint(['organization_id'], ['organization.id']),
        sa.ForeignKeyConstraint(['till_id'], ['till.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_till_session_created_session', 'till_session', ['till_id', 'created_at'])
    op.create_index('ix_till_session_operator_created', 'till_session', ['operator_id', 'created_at'])
    op.create_index('ix_till_session_organization_id', 'till_session', ['organization_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_till_session_organization_id', table_name='till_session')
    op.drop_index('ix_till_session_operator_created', table_name='till_session')
    op.drop_index('ix_till_session_created_session', table_name='till_session')
    op.drop_table('till_session')
    op.drop_index('ix_sale_item_sale_id', table_name='sale_item')
    op.drop_table('sale_item')
    op.drop_index('ix_sale_organization_created', table_name='sale')
    op.drop_index('ix_sale_created_till', table_name='sale')
    op.drop_table('sale')
    op.drop_index('ix_inventory_movement_product_created', table_name='inventory_movement')
    op.drop_index('ix_inventory_movement_organization_created', table_name='inventory_movement')
    op.drop_index('ix_inventory_movement_location_created', table_name='inventory_movement')
    op.drop_index('ix_inventory_movement_created_at', table_name='inventory_movement')
    op.drop_table('inventory_movement')
    op.drop_index('ix_stock_organization_id', table_name='stock')
    op.drop_table('stock')
    op.drop_index('ix_subscription_organization_id', table_name='subscription')
    op.drop_table('subscription')
    op.drop_index('ix_till_organization_id', table_name='till')
    op.drop_index('ix_till_location_id', table_name='till')
    op.drop_index('ix_till_is_active', table_name='till')
    op.drop_table('till')
    op.drop_index('ix_product_organization_id', table_name='product')
    op.drop_index('ix_product_is_active', table_name='product')
    op.drop_table('product')
    op.drop_index('ix_location_organization_id', table_name='location')
    op.drop_index('ix_location_is_active', table_name='location')
    op.drop_table('location')
    op.drop_index('ix_user_organization_id', table_name='user')
    op.drop_index('ix_user_is_active', table_name='user')
    op.drop_index('ix_user_email', table_name='user')
    op.drop_table('user')
    op.drop_index('ix_organization_name', table_name='organization')
    op.drop_index('ix_organization_is_active', table_name='organization')
    op.drop_index('ix_organization_code', table_name='organization')
    op.drop_table('organization')
