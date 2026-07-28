"""login_attempts — bộ đếm chặn dò mật khẩu, chuyển từ RAM sang DB

Trước đây số lần đăng nhập sai đếm bằng dict trong tiến trình: mất sạch khi
restart server, mỗi worker đếm riêng nên ngưỡng thực tế bị nhân lên, và dict
phình mãi vì không bao giờ dọn.

Bảng này KHÔNG phải nhật ký — mỗi IP đúng một dòng, ghi đè tại chỗ. Lịch sử
đăng nhập sai vẫn nằm ở audit_events (action LOGIN_FAILURE).

Revision ID: v21f0f000021
Revises: u20f0f000020
Create Date: 2026-07-27
"""
from alembic import op
import sqlalchemy as sa


revision = "v21f0f000021"
down_revision = "u20f0f000020"
branch_labels = None
depends_on = None


def _has_table(connection, name: str) -> bool:
    return sa.inspect(connection).has_table(name)


def upgrade() -> None:
    connection = op.get_bind()
    if _has_table(connection, "login_attempts"):
        return
    op.create_table(
        "login_attempts",
        sa.Column("ip", sa.String(), primary_key=True),
        sa.Column("failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocked_until", sa.String(), nullable=False, server_default=""),
        sa.Column("updated_at", sa.String(), nullable=False, server_default=""),
    )
    # Dọn định kỳ lọc theo updated_at (xem _purge_stale_login_attempts).
    op.create_index(
        "ix_login_attempts_updated_at", "login_attempts", ["updated_at"]
    )


def downgrade() -> None:
    connection = op.get_bind()
    if not _has_table(connection, "login_attempts"):
        return
    op.drop_index("ix_login_attempts_updated_at", table_name="login_attempts")
    op.drop_table("login_attempts")
