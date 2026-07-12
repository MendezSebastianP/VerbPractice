"""ai_usage_logs

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-30 13:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "ai_usage_logs" in inspector.get_table_names():
        return

    op.create_table(
        "ai_usage_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("feature", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("input_cost_per_million", sa.Float(), nullable=False, server_default="0"),
        sa.Column("output_cost_per_million", sa.Float(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="success"),
        sa.Column("request_label", sa.String(length=255), nullable=True),
        sa.Column("extra_data", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f("ix_ai_usage_logs_created_at"), "ai_usage_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_ai_usage_logs_feature"), "ai_usage_logs", ["feature"], unique=False)
    op.create_index(op.f("ix_ai_usage_logs_model"), "ai_usage_logs", ["model"], unique=False)
    op.create_index(op.f("ix_ai_usage_logs_status"), "ai_usage_logs", ["status"], unique=False)
    op.create_index(op.f("ix_ai_usage_logs_user_id"), "ai_usage_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_usage_logs_user_id"), table_name="ai_usage_logs")
    op.drop_index(op.f("ix_ai_usage_logs_status"), table_name="ai_usage_logs")
    op.drop_index(op.f("ix_ai_usage_logs_model"), table_name="ai_usage_logs")
    op.drop_index(op.f("ix_ai_usage_logs_feature"), table_name="ai_usage_logs")
    op.drop_index(op.f("ix_ai_usage_logs_created_at"), table_name="ai_usage_logs")
    op.drop_table("ai_usage_logs")
