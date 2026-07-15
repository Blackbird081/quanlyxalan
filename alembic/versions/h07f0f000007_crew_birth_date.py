"""add optional crew birth date

Revision ID: h07f0f000007
Revises: g06f0f000006
Create Date: 2026-07-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "h07f0f000007"
down_revision = "g06f0f000006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("crew_members")}
    if "birth_date" not in columns:
        with op.batch_alter_table("crew_members") as batch_op:
            batch_op.add_column(sa.Column("birth_date", sa.String(), nullable=True))


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("crew_members")}
    if "birth_date" in columns:
        with op.batch_alter_table("crew_members") as batch_op:
            batch_op.drop_column("birth_date")
