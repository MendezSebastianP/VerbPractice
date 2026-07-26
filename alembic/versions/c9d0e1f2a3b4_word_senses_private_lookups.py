"""word senses and private contextual lookups

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-07-23 20:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "c9d0e1f2a3b4"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "word_senses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "word_id",
            sa.Integer(),
            sa.ForeignKey("words.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sense_key", sa.String(length=255), nullable=False),
        sa.Column("part_of_speech", sa.String(length=32), nullable=True),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("synonyms", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("examples", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column(
            "source",
            sa.String(length=64),
            nullable=False,
            server_default="offline_dictionary",
        ),
        sa.Column("source_version", sa.String(length=64), nullable=True),
        sa.Column(
            "is_trusted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("embedding_model", sa.String(length=128), nullable=True),
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
        sa.UniqueConstraint("word_id", "sense_key", name="uq_word_sense_key"),
    )
    op.create_index(
        op.f("ix_word_senses_word_id"), "word_senses", ["word_id"], unique=False
    )

    op.create_table(
        "word_sense_translations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "sense_id",
            sa.Integer(),
            sa.ForeignKey("word_senses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_language_id",
            sa.Integer(),
            sa.ForeignKey("languages.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("translation", sa.String(length=256), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "source",
            sa.String(length=64),
            nullable=False,
            server_default="offline_dictionary",
        ),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "sense_id",
            "target_language_id",
            "translation",
            name="uq_word_sense_translation",
        ),
    )
    op.create_index(
        op.f("ix_word_sense_translations_sense_id"),
        "word_sense_translations",
        ["sense_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_word_sense_translations_target_language_id"),
        "word_sense_translations",
        ["target_language_id"],
        unique=False,
    )

    with op.batch_alter_table("user_added_words") as batch:
        batch.add_column(sa.Column("selected_sense_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_user_added_words_selected_sense_id",
            "word_senses",
            ["selected_sense_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_index(
            "ix_user_added_words_selected_sense_id",
            ["selected_sense_id"],
            unique=False,
        )

    op.create_table(
        "user_word_lookups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "word_id",
            sa.Integer(),
            sa.ForeignKey("words.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "selected_sense_id",
            sa.Integer(),
            sa.ForeignKey("word_senses.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "source_language_id",
            sa.Integer(),
            sa.ForeignKey("languages.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "target_language_id",
            sa.Integer(),
            sa.ForeignKey("languages.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column(
            "context_source",
            sa.String(length=16),
            nullable=False,
            server_default="manual",
        ),
        sa.Column("result_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("ranking_method", sa.String(length=64), nullable=True),
        sa.Column("ranking_score", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    for column in (
        "created_at",
        "selected_sense_id",
        "source_language_id",
        "target_language_id",
        "user_id",
        "word_id",
    ):
        op.create_index(
            op.f(f"ix_user_word_lookups_{column}"),
            "user_word_lookups",
            [column],
            unique=False,
        )
    op.create_index(
        "ix_user_word_lookups_user_created",
        "user_word_lookups",
        ["user_id", "created_at"],
        unique=False,
    )

    # Preserve the current cache as one legacy sense per lexical entry. This
    # gives existing installations an immediately usable sense inventory.
    bind = op.get_bind()
    word_senses_table = sa.table(
        "word_senses",
        sa.column("id", sa.Integer()),
        sa.column("word_id", sa.Integer()),
        sa.column("sense_key", sa.String()),
        sa.column("definition", sa.Text()),
        sa.column("synonyms", sa.JSON()),
        sa.column("examples", sa.JSON()),
        sa.column("source", sa.String()),
        sa.column("source_version", sa.String()),
        sa.column("is_trusted", sa.Boolean()),
        sa.column("is_primary", sa.Boolean()),
    )
    sense_translations_table = sa.table(
        "word_sense_translations",
        sa.column("sense_id", sa.Integer()),
        sa.column("target_language_id", sa.Integer()),
        sa.column("translation", sa.String()),
        sa.column("note", sa.Text()),
        sa.column("source", sa.String()),
        sa.column("priority", sa.Integer()),
    )
    lexical_entries_table = sa.table(
        "word_lexical_entries",
        sa.column("id", sa.Integer()),
        sa.column("word_id", sa.Integer()),
        sa.column("definition", sa.Text()),
        sa.column("synonyms", sa.JSON()),
        sa.column("examples", sa.JSON()),
        sa.column("source", sa.String()),
    )
    native_translations_table = sa.table(
        "word_native_translations",
        sa.column("id", sa.Integer()),
        sa.column("word_id", sa.Integer()),
        sa.column("native_language_id", sa.Integer()),
        sa.column("translation", sa.String()),
        sa.column("note", sa.Text()),
        sa.column("source", sa.String()),
        sa.column("priority", sa.Integer()),
    )
    lexical_rows = bind.execute(
        sa.select(lexical_entries_table).order_by(lexical_entries_table.c.id)
    ).mappings()
    sense_by_word: dict[int, int] = {}
    for row in lexical_rows:
        result = bind.execute(
            word_senses_table.insert()
            .values(
                word_id=row["word_id"],
                sense_key=f"legacy:{row['id']}",
                definition=row["definition"],
                synonyms=row["synonyms"],
                examples=row["examples"],
                source=row["source"],
                source_version=revision,
                is_trusted=False,
                is_primary=True,
            )
            .returning(word_senses_table.c.id)
        )
        sense_by_word[row["word_id"]] = int(result.scalar_one())

    native_rows = bind.execute(
        sa.select(native_translations_table).order_by(
            native_translations_table.c.id
        )
    ).mappings()
    for row in native_rows:
        sense_id = sense_by_word.get(row["word_id"])
        if sense_id is None:
            continue
        bind.execute(
            sense_translations_table.insert().values(
                sense_id=sense_id,
                target_language_id=row["native_language_id"],
                translation=row["translation"],
                note=row["note"],
                source=row["source"],
                priority=row["priority"],
            )
        )

    for word_id, sense_id in sense_by_word.items():
        bind.execute(
            sa.text(
                """
                UPDATE user_added_words
                SET selected_sense_id = :sense_id
                WHERE word_id = :word_id AND selected_sense_id IS NULL
                """
            ),
            {"sense_id": sense_id, "word_id": word_id},
        )


def downgrade() -> None:
    op.drop_index(
        "ix_user_word_lookups_user_created", table_name="user_word_lookups"
    )
    for column in (
        "word_id",
        "user_id",
        "target_language_id",
        "source_language_id",
        "selected_sense_id",
        "created_at",
    ):
        op.drop_index(
            op.f(f"ix_user_word_lookups_{column}"),
            table_name="user_word_lookups",
        )
    op.drop_table("user_word_lookups")

    with op.batch_alter_table("user_added_words") as batch:
        batch.drop_index("ix_user_added_words_selected_sense_id")
        batch.drop_constraint(
            "fk_user_added_words_selected_sense_id", type_="foreignkey"
        )
        batch.drop_column("selected_sense_id")

    op.drop_index(
        op.f("ix_word_sense_translations_target_language_id"),
        table_name="word_sense_translations",
    )
    op.drop_index(
        op.f("ix_word_sense_translations_sense_id"),
        table_name="word_sense_translations",
    )
    op.drop_table("word_sense_translations")
    op.drop_index(op.f("ix_word_senses_word_id"), table_name="word_senses")
    op.drop_table("word_senses")
