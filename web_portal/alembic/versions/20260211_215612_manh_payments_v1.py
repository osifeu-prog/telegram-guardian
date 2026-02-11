\"\"\"MANH payments V1: invoices + purchases + withdrawals

Revision ID: 20260211_215612_manh_payments_v1
Revises: ca606197b19a
Create Date: 2026-02-11T21:56:12
\"\"\"

from alembic import op
import sqlalchemy as sa

revision = "20260211_215612_manh_payments_v1"
down_revision = "ca606197b19a"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "manh_invoices",
        sa.Column("invoice_id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("ils_amount", sa.Numeric(38, 9), nullable=False),
        sa.Column("manh_amount", sa.Numeric(38, 9), nullable=False),
        sa.Column("ton_amount", sa.Numeric(38, 9), nullable=False),
        sa.Column("ton_ils_rate", sa.Numeric(38, 9), nullable=False),
        sa.Column("ton_treasury_address", sa.String(length=128), nullable=False),
        sa.Column("comment", sa.String(length=256), nullable=False),
        sa.Column("sig16", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_manh_invoices_user", "manh_invoices", ["user_id", "created_at"])

    op.create_table(
        "manh_purchases",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("invoice_id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("manh_amount", sa.Numeric(38, 9), nullable=False),
        sa.Column("ils_amount", sa.Numeric(38, 9), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("invoice_id", name="uq_manh_purchases_invoice"),
    )
    op.create_index("ix_manh_purchases_user", "manh_purchases", ["user_id", "created_at"])

    op.create_table(
        "manh_withdrawals",
        sa.Column("withdrawal_id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("amount_manh", sa.Numeric(38, 9), nullable=False),
        sa.Column("target_ton_address", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'REQUESTED'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by", sa.String(length=64), nullable=True),
        sa.Column("note", sa.String(length=512), nullable=True),
    )
    op.create_index("ix_manh_withdrawals_user", "manh_withdrawals", ["user_id", "created_at"])


def downgrade():
    op.drop_index("ix_manh_withdrawals_user", table_name="manh_withdrawals")
    op.drop_table("manh_withdrawals")
    op.drop_index("ix_manh_purchases_user", table_name="manh_purchases")
    op.drop_table("manh_purchases")
    op.drop_index("ix_manh_invoices_user", table_name="manh_invoices")
    op.drop_table("manh_invoices")
