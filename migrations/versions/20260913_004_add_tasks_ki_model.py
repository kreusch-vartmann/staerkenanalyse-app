"""add tasks.ki_model and align nullability

Revision ID: 20260913_004
Revises: 20260213_003
"""
from alembic import op
import sqlalchemy as sa

revision = '20260913_004'
down_revision = '20260213_003'


def upgrade():
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("tasks")}
    if "ki_model" not in cols:
        op.add_column("tasks", sa.Column("ki_model", sa.String(20), nullable=True))
    
    # Längen-Drift angleichen: Modell sagt String(50), Migration hat String(100)
    with op.batch_alter_table("tasks") as batch:
        batch.alter_column("observation_area",
                          existing_type=sa.String(100),
                          type_=sa.String(50),
                          existing_nullable=False)


def downgrade():
    op.drop_column("tasks", "ki_model")
