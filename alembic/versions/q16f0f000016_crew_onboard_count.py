"""declarations.crew_onboard_count: actual crew headcount for this call

crew_count already exists but represents the vessel's minimum required crew
per its GCN (locked, copied from the vessel profile) — not how many crew are
actually aboard for this specific trip. That figure has no home: the crew
checklist only counts named individuals with a registered profile, which is
often empty for vessels whose crew roster hasn't been entered yet. This
revision adds a separate, always-editable headcount field for that.

Revision ID: q16f0f000016
Revises: p15f0f000015
Create Date: 2026-07-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "q16f0f000016"
down_revision = "p15f0f000015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {c["name"] for c in inspect(op.get_bind()).get_columns("declarations")}
    with op.batch_alter_table("declarations") as batch_op:
        if "crew_onboard_count" not in columns:
            batch_op.add_column(sa.Column(
                "crew_onboard_count", sa.Integer(), nullable=False, server_default="0"
            ))


def downgrade() -> None:
    columns = {c["name"] for c in inspect(op.get_bind()).get_columns("declarations")}
    with op.batch_alter_table("declarations") as batch_op:
        if "crew_onboard_count" in columns:
            batch_op.drop_column("crew_onboard_count")
