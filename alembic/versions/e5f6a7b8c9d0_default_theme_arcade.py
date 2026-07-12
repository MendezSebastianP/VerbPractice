"""default_theme_arcade

Arcade becomes the default theme. Existing profiles on "light" got it from the
old registration hard-code rather than an explicit pick, so they move to the
new default once; a theme picked after this migration persists as usual.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-12 12:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text("UPDATE user_profiles SET theme_preference = 'arcade' WHERE theme_preference = 'light'")
    )


def downgrade() -> None:
    op.execute(
        sa.text("UPDATE user_profiles SET theme_preference = 'light' WHERE theme_preference = 'arcade'")
    )
