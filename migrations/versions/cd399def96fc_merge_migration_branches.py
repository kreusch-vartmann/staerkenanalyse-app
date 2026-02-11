"""Merge migration branches

Revision ID: cd399def96fc
Revises: add_group_tasks_ki_model_001, d19bbd077f38
Create Date: 2026-02-11 11:24:18.601629

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cd399def96fc'
down_revision = ('add_group_tasks_ki_model_001', 'd19bbd077f38')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
