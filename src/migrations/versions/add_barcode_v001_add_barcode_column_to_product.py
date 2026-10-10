"""Add barcode column to product

Revision ID: add_barcode_v001
Revises: b143c7e5867b
Create Date: 2026-10-10 05:28:09.505669

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_barcode_v001'
down_revision: Union[str, Sequence[str], None] = 'b143c7e5867b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add barcode column to product table
    # barcode is nullable to support products without barcodes
    # Uniqueness is per-organization (not global) but not enforced via constraint
    # Applications should enforce this in business logic
    op.add_column('product', sa.Column('barcode', sa.String(100), nullable=True))
    
    # Create index on barcode for faster lookups
    op.create_index('ix_product_barcode', 'product', ['barcode'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop barcode index and column
    op.drop_index('ix_product_barcode', table_name='product')
    op.drop_column('product', 'barcode')
