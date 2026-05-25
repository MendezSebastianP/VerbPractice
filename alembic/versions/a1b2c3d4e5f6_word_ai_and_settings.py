"""word_ai_and_settings

Adds:
- UserPreference: language/display/last-choice columns
- WordLexicalEntry, WordNativeTranslation (split AI cache)
- UserAddedWord (priority queue)
- TranslationReport (feedback)

Revision ID: a1b2c3d4e5f6
Revises: 8d4ee9817f62
Create Date: 2026-05-24 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "8d4ee9817f62"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("user_preferences") as batch:
        batch.add_column(
            sa.Column(
                "mother_tongue_language_id",
                sa.Integer(),
                sa.ForeignKey("languages.id", ondelete="SET NULL"),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column(
                "learning_language_id",
                sa.Integer(),
                sa.ForeignKey("languages.id", ondelete="SET NULL"),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column(
                "translation_display_mode",
                sa.String(length=32),
                nullable=False,
                server_default="partial",
            )
        )
        batch.add_column(
            sa.Column(
                "force_unlock_added_words",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            )
        )
        batch.add_column(sa.Column("last_practice_pair", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("last_practice_mode", sa.String(length=32), nullable=True))

    op.create_table(
        "word_lexical_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "word_id",
            sa.Integer(),
            sa.ForeignKey("words.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("synonyms", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("examples", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("extended_content", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="ai"),
        sa.Column("flag_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "word_native_translations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "word_id",
            sa.Integer(),
            sa.ForeignKey("words.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "native_language_id",
            sa.Integer(),
            sa.ForeignKey("languages.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("translation", sa.String(length=256), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="ai"),
        sa.Column("flag_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("word_id", "native_language_id", name="uq_word_native_translation"),
    )

    op.create_table(
        "user_added_words",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "word_id",
            sa.Integer(),
            sa.ForeignKey("words.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("language_pair", sa.String(length=16), nullable=False, index=True),
        sa.Column("context_hint", sa.Text(), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "word_id", "language_pair", name="uq_user_added_word"),
    )

    op.create_table(
        "translation_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("entry_type", sa.String(length=16), nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending", index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "resolver_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("translation_reports")
    op.drop_table("user_added_words")
    op.drop_table("word_native_translations")
    op.drop_table("word_lexical_entries")
    with op.batch_alter_table("user_preferences") as batch:
        batch.drop_column("last_practice_mode")
        batch.drop_column("last_practice_pair")
        batch.drop_column("force_unlock_added_words")
        batch.drop_column("translation_display_mode")
        batch.drop_column("learning_language_id")
        batch.drop_column("mother_tongue_language_id")
