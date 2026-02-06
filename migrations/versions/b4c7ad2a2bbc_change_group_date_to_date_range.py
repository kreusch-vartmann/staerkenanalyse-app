"""change_group_date_to_date_range

Revision ID: b4c7ad2a2bbc
Revises: 37910f5c8ff0
Create Date: 2026-02-06 15:25:30.298874

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b4c7ad2a2bbc'
down_revision = '37910f5c8ff0'
branch_labels = None
depends_on = None


def upgrade():
    # Umbenennen von 'date' zu 'date_from'
    op.alter_column('groups', 'date', new_column_name='date_from')
    # Hinzufügen der neuen Spalte 'date_to'
    op.add_column('groups', sa.Column('date_to', sa.Date(), nullable=True))


def downgrade():
    # Entfernen von 'date_to'
    op.drop_column('groups', 'date_to')
    # Zurückbenennen von 'date_from' zu 'date'
    op.alter_column('groups', 'date_from', new_column_name='date')
