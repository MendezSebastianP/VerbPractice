"""tags.applies_to drift fix

Adds tags.applies_to if missing — covers DBs where b2c3d4e5f6a7 was recorded
as applied but the column never landed (schema drift).

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-26 20:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.core.tags import CURATED_TAGS


revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("tags")}
    if "applies_to" in columns:
        return

    op.add_column(
        "tags",
        sa.Column("applies_to", sa.JSON(), nullable=False, server_default="[]"),
    )

    tags_table = sa.table(
        "tags",
        sa.column("slug", sa.String()),
        sa.column("applies_to", sa.JSON()),
    )
    for tag in CURATED_TAGS:
        op.execute(
            tags_table.update()
            .where(tags_table.c.slug == tag.slug)
            .values(applies_to=list(tag.applies_to))
        )

    op.alter_column("tags", "applies_to", server_default=None)


def downgrade() -> None:
    op.drop_column("tags", "applies_to")
