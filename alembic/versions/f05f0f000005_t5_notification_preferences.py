"""t5_notification_preferences

Revision ID: f05f0f000005
Revises: e04f0f000004
Create Date: 2026-07-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "f05f0f000005"
down_revision = "e04f0f000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("users")}
    if "notification_preferences_json" not in columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(sa.Column(
                "notification_preferences_json", sa.Text(), nullable=False,
                server_default='{"in_app_certificate_reminders":true}',
            ))


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("users")}
    if "notification_preferences_json" in columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("notification_preferences_json")
