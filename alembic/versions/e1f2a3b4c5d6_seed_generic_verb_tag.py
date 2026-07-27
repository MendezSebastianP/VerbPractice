"""seed generic verb tag

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-07-27 09:20:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "e1f2a3b4c5d6"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None


def _tags_table() -> sa.TableClause:
    return sa.table(
        "tags",
        sa.column("slug", sa.String()),
        sa.column("display_name", sa.String()),
        sa.column("kind", sa.String()),
        sa.column("applies_to", sa.JSON()),
    )


def upgrade() -> None:
    bind = op.get_bind()
    tags = _tags_table()
    existing = bind.execute(
        sa.select(tags.c.slug).where(tags.c.slug == "verb")
    ).scalar_one_or_none()
    values = {
        "display_name": "Verb",
        "kind": "grammatical",
        "applies_to": ["word", "verb"],
    }
    if existing is None:
        bind.execute(tags.insert().values(slug="verb", **values))
    else:
        bind.execute(
            tags.update().where(tags.c.slug == "verb").values(**values)
        )


def downgrade() -> None:
    bind = op.get_bind()
    tags = _tags_table()
    tag_id = bind.execute(
        sa.text("SELECT id FROM tags WHERE slug = 'verb'")
    ).scalar_one_or_none()
    if tag_id is None:
        return
    word_uses = bind.execute(
        sa.text("SELECT 1 FROM word_tags WHERE tag_id = :tag_id LIMIT 1"),
        {"tag_id": tag_id},
    ).first()
    verb_uses = bind.execute(
        sa.text("SELECT 1 FROM verb_tags WHERE tag_id = :tag_id LIMIT 1"),
        {"tag_id": tag_id},
    ).first()
    if word_uses is None and verb_uses is None:
        bind.execute(tags.delete().where(tags.c.slug == "verb"))
