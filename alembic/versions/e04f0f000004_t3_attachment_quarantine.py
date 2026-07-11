"""t3_attachment_quarantine

Revision ID: e04f0f000004
Revises: d03f0f000003
Create Date: 2026-07-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "e04f0f000004"
down_revision = "d03f0f000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {c["name"] for c in inspect(op.get_bind()).get_columns("attachments")}
    with op.batch_alter_table("attachments") as batch_op:
        if "checksum_sha256" not in columns:
            batch_op.add_column(sa.Column("checksum_sha256", sa.String(), nullable=False, server_default=""))
        if "scan_status" not in columns:
            batch_op.add_column(sa.Column("scan_status", sa.String(), nullable=False, server_default="QUARANTINED"))
        if "storage_backend" not in columns:
            batch_op.add_column(sa.Column("storage_backend", sa.String(), nullable=False, server_default="LOCAL_QUARANTINE"))
        if "scanned_at" not in columns:
            batch_op.add_column(sa.Column("scanned_at", sa.String(), nullable=True))


def downgrade() -> None:
    columns = {c["name"] for c in inspect(op.get_bind()).get_columns("attachments")}
    with op.batch_alter_table("attachments") as batch_op:
        for name in ("scanned_at", "storage_backend", "scan_status", "checksum_sha256"):
            if name in columns:
                batch_op.drop_column(name)
