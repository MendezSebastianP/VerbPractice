"""multi_translation_tags_sets

- word_native_translations: drop unique(word_id, native_language_id),
  add (word_id, native_language_id, translation) unique + priority col.
- tags + word_tags
- word_sets + word_set_members
- Seed curated tag vocabulary rows.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-24 12:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.core.tags import tag_seed_rows


revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # word_native_translations: priority col + swap unique constraint
    with op.batch_alter_table("word_native_translations") as batch:
        batch.add_column(sa.Column("priority", sa.Integer(), nullable=False, server_default="0"))
        batch.drop_constraint("uq_word_native_translation", type_="unique")
        batch.create_unique_constraint(
            "uq_word_native_translation",
            ["word_id", "native_language_id", "translation"],
        )

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=64), nullable=False, unique=True, index=True),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False, server_default="thematic"),
        sa.Column("applies_to", sa.JSON(), nullable=False),
        sa.Column(
            "created_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "word_tags",
        sa.Column(
            "word_id",
            sa.Integer(),
            sa.ForeignKey("words.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tag_id",
            sa.Integer(),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="user"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "verb_tags",
        sa.Column(
            "verb_id",
            sa.Integer(),
            sa.ForeignKey("verbs.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tag_id",
            sa.Integer(),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="user"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "word_sets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "owner_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(length=32), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="manual"),
        sa.Column("filter_tag_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "word_set_members",
        sa.Column(
            "set_id",
            sa.Integer(),
            sa.ForeignKey("word_sets.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "word_id",
            sa.Integer(),
            sa.ForeignKey("words.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Seed curated tag vocabulary
    tags_table = sa.table(
        "tags",
        sa.column("slug", sa.String),
        sa.column("display_name", sa.String),
        sa.column("kind", sa.String),
        sa.column("applies_to", sa.JSON()),
    )
    op.bulk_insert(tags_table, tag_seed_rows())


def downgrade() -> None:
    op.drop_table("word_set_members")
    op.drop_table("word_sets")
    op.drop_table("verb_tags")
    op.drop_table("word_tags")
    op.drop_table("tags")
    with op.batch_alter_table("word_native_translations") as batch:
        batch.drop_constraint("uq_word_native_translation", type_="unique")
        batch.create_unique_constraint(
            "uq_word_native_translation",
            ["word_id", "native_language_id"],
        )
        batch.drop_column("priority")
