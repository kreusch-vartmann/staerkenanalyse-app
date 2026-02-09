"""Merge auth and initial migrations

Revision ID: 07bf8118a3c8
Revises: 65898bde1230, add_auth_models_001
Create Date: 2026-02-09 09:42:31.291261

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '07bf8118a3c8'
down_revision = ('65898bde1230', 'add_auth_models_001')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
