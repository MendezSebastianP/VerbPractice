"""add CEFR levels to words and verbs

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-07-26 12:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "d0e1f2a3b4c5"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


CEFR_CHECK = "cefr_level IS NULL OR cefr_level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')"


def upgrade() -> None:
    with op.batch_alter_table("words") as batch:
        batch.add_column(sa.Column("cefr_level", sa.String(length=2), nullable=True))
        batch.create_check_constraint("ck_words_cefr_level", CEFR_CHECK)
        batch.create_index("ix_words_cefr_level", ["cefr_level"], unique=False)

    with op.batch_alter_table("verbs") as batch:
        batch.add_column(sa.Column("cefr_level", sa.String(length=2), nullable=True))
        batch.create_check_constraint("ck_verbs_cefr_level", CEFR_CHECK)
        batch.create_index("ix_verbs_cefr_level", ["cefr_level"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("verbs") as batch:
        batch.drop_index("ix_verbs_cefr_level")
        batch.drop_constraint("ck_verbs_cefr_level", type_="check")
        batch.drop_column("cefr_level")

    with op.batch_alter_table("words") as batch:
        batch.drop_index("ix_words_cefr_level")
        batch.drop_constraint("ck_words_cefr_level", type_="check")
        batch.drop_column("cefr_level")
