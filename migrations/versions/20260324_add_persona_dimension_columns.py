"""add persona dimension columns

Revision ID: 20260324_add_persona_dimension_columns
Revises: None
Create Date: 2026-03-24
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260324_add_persona_dimension_columns"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("personas") as batch_op:
        batch_op.add_column(sa.Column("occupation_category", sa.String(), nullable=True, server_default=""))
        batch_op.add_column(sa.Column("region", sa.String(), nullable=True, server_default=""))
        batch_op.add_column(sa.Column("household_type", sa.String(), nullable=True, server_default=""))
        batch_op.add_column(sa.Column("buy_channel", sa.String(), nullable=True, server_default=""))
        batch_op.add_column(sa.Column("product_group", sa.String(), nullable=True, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("personas") as batch_op:
        batch_op.drop_column("product_group")
        batch_op.drop_column("buy_channel")
        batch_op.drop_column("household_type")
        batch_op.drop_column("region")
        batch_op.drop_column("occupation_category")
