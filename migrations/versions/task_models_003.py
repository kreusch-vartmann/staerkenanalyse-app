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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # Create task_versions table first (no foreign key to tasks yet)
    if 'task_versions' not in existing_tables:
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
    if 'tasks' not in existing_tables:
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
    inspector = sa.inspect(bind)
    fk_names = {fk.get('name') for fk in inspector.get_foreign_keys('task_versions')}
    if 'fk_task_versions_task_id' not in fk_names:
        with op.batch_alter_table('task_versions') as batch_op:
            batch_op.create_foreign_key(
                'fk_task_versions_task_id',
                'tasks',
                ['task_id'],
                ['id']
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # Drop foreign key
    if 'task_versions' in existing_tables:
        fk_names = {fk.get('name') for fk in inspector.get_foreign_keys('task_versions')}
        if 'fk_task_versions_task_id' in fk_names:
            with op.batch_alter_table('task_versions') as batch_op:
                batch_op.drop_constraint('fk_task_versions_task_id', type_='foreignkey')

    # Drop tables
    if 'tasks' in existing_tables:
        op.drop_table('tasks')
    if 'task_versions' in existing_tables:
        op.drop_table('task_versions')
