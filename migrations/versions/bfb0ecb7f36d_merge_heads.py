"""merge heads

Revision ID: bfb0ecb7f36d
Revises: add_prompt_default_001, cd399def96fc
Create Date: 2026-02-13 07:36:45.982800

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bfb0ecb7f36d'
down_revision = ('add_prompt_default_001', 'cd399def96fc')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
