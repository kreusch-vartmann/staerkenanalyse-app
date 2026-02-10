"""Add Task and TaskVersion models for Phase 2

Revision ID: task_models_003
Revises: add_auth_models_001
Create Date: 2026-02-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'task_models_003'
down_revision = 'add_auth_models_001'
branch_labels = None
depends_on = None


def upgrade():
    # Create task_versions table first (no foreign key to tasks yet)
    op.create_table(
        'task_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('version_number', sa.Float(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('context_data', sa.Text(), nullable=True),
        sa.Column('change_notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create tasks table
    op.create_table(
        'tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('observation_area', sa.String(length=100), nullable=False),
        sa.Column('participant_count', sa.Integer(), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('current_version_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['current_version_id'], ['task_versions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add foreign key from task_versions.task_id to tasks.id
    op.create_foreign_key(
        'fk_task_versions_task_id',
        'task_versions', 'tasks',
        ['task_id'], ['id']
    )


def downgrade():
    # Drop foreign key
    op.drop_constraint('fk_task_versions_task_id', 'task_versions', type_='foreignkey')
    
    # Drop tables
    op.drop_table('tasks')
    op.drop_table('task_versions')
