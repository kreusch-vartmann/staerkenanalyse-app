"""Add User, Role, and user_groups for authentication

Revision ID: add_auth_models_001
Revises: 1bb5bd2a5c04
Create Date: 2026-02-09 10:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_auth_models_001'
down_revision = '1bb5bd2a5c04'
branch_labels = None
depends_on = None


def upgrade():
    """Create role, user, and user_groups tables."""
    
    # Create roles table
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False, index=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('force_password_change', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    # Create user_groups junction table (M2M)
    op.create_table(
        'user_groups',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('user_id', 'group_id')
    )

    # Inser standard roles
    op.execute(
        "INSERT INTO roles (name, description) VALUES ('admin', 'Vollzugriff auf alle Funktionen')"
    )
    op.execute(
        "INSERT INTO roles (name, description) VALUES ('beobachter', 'Zugriff auf zugewiesene Gruppen')"
    )


def downgrade():
    """Drop auth tables."""
    op.drop_table('user_groups')
    op.drop_table('users')
    op.drop_table('roles')
