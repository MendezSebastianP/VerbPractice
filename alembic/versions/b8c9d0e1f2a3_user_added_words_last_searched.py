"""user_added_words_last_searched

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-07-19 10:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("user_added_words") as batch:
        batch.add_column(
            sa.Column(
                "last_searched_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("user_added_words") as batch:
        batch.drop_column("last_searched_at")
