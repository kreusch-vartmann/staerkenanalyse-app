"""add prompt default flag

Revision ID: add_prompt_default_001
Revises: add_group_tasks_ki_model_001
Create Date: 2026-02-10T00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_prompt_default_001'
down_revision = 'add_group_tasks_ki_model_001'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'prompts',
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade():
    op.drop_column('prompts', 'is_default')
