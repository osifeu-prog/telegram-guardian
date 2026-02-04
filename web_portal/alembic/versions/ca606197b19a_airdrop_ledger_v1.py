"""airdrop ledger v1

Revision ID: airdrop_ledger_v1
Revises: 0001_init
Create Date: 2026-02-04
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# IMPORTANT:
# adjust down_revision if your real previous revision id differs from 0001_init
revision = "ca606197b19a"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users: add airdrop fields (safe if missing)
    with op.batch_alter_table("users") as b:
        b.add_column(sa.Column("first_name", sa.String(length=128), nullable=True))
        b.add_column(sa.Column("language_code", sa.String(length=16), nullable=True))
        b.add_column(sa.Column("airdrop_claimed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        b.add_column(sa.Column("balance", sa.Integer(), nullable=False, server_default=sa.text("0")))

    # ledger_events
    op.create_table(
        "ledger_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("telegram_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ledger_events_telegram_id", "ledger_events", ["telegram_id"])


def downgrade() -> None:
    op.drop_index("ix_ledger_events_telegram_id", table_name="ledger_events")
    op.drop_table("ledger_events")
    with op.batch_alter_table("users") as b:
        b.drop_column("balance")
        b.drop_column("airdrop_claimed")
        b.drop_column("language_code")
        b.drop_column("first_name")