"""stamp final revision - force single head

Revision ID: stamp_final_20260219_153823
Revises: 
Create Date: 2026-02-19 15:38:23.564348

"""
from alembic import op

revision = 'stamp_final_20260219_153823'
down_revision = 'add_chat_ids_20260219_145003'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("DELETE FROM alembic_version")
    op.execute("INSERT INTO alembic_version (version_num) VALUES ('stamp_final_20260219_153823')")

def downgrade():
    op.execute("DELETE FROM alembic_version")


