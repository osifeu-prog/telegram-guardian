"""add chat_ids table

Revision ID: add_chat_ids_20260219_145003
Revises: 
Create Date: 2026-02-19 14:50:03.142340

"""
from alembic import op
import sqlalchemy as sa

revision = 'add_chat_ids_20260219_145003'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('chat_ids',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('first_seen', sa.DateTime(), nullable=True),
        sa.Column('last_interaction', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chat_id')
    )

def downgrade():
    op.drop_table('chat_ids')




