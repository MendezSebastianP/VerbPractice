"""add_user_admin_flag

Revision ID: 8d4ee9817f62
Revises: 1f460095e63c
Create Date: 2026-03-30 23:46:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8d4ee9817f62'
down_revision = '1f460095e63c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('is_admin', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    )


def downgrade() -> None:
    op.drop_column('users', 'is_admin')
