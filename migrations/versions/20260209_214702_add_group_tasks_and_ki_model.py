"""add group_tasks and ki_model

Revision ID: add_group_tasks_ki_model_001
Revises: 
Create Date: 2026-02-09T21:47:02.572209

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_group_tasks_ki_model_001'
down_revision = '07bf8118a3c8'
branch_labels = None
depends_on = None


def upgrade():
    # Create group_tasks association table
    op.create_table(
        'group_tasks',
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
        sa.PrimaryKeyConstraint('group_id', 'task_id')
    )
    
    # Add ki_model column to participants table
    op.add_column('participants', sa.Column('ki_model', sa.String(20), nullable=True))


def downgrade():
    # Remove ki_model column
    op.drop_column('participants', 'ki_model')
    
    # Drop group_tasks table
    op.drop_table('group_tasks')
