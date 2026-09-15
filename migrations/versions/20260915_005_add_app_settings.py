"""add app_settings table for encrypted API keys

Revision ID: 20260915_005
Revises: 20260913_004
Create Date: 2026-09-15

Speichert verschlüsselte App-Einstellungen (z. B. API-Keys), damit Admins
KI-Provider über die UI konfigurieren können, ohne Container-Redeploy.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260915_005"
down_revision = "20260913_004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value_encrypted", sa.String(length=500), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], name="fk_app_settings_updated_by"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_app_settings_key"),
    )


def downgrade():
    op.drop_table("app_settings")
