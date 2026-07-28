"""users.password_changed_at — revoke old JWTs when a password changes

Trước đây đổi/reset mật khẩu không có tác dụng thu hồi token JWT đã phát hành
— token cũ vẫn dùng được tới hết ACCESS_TOKEN_EXPIRE_MINUTES (mặc định 24h)
dù mật khẩu vừa bị đổi vì nghi lộ hoặc thiết bị bị mất. Token giờ mang theo
mốc mật khẩu tại lúc phát hành (claim pwd_ts); get_current_user so sánh với
password_changed_at hiện tại trên mỗi request.

Người dùng đã tồn tại trước migration này được gán password_changed_at =
created_at (không có mốc thật nào sớm hơn để dùng) — không thu hồi token nào
đang có hiệu lực tại thời điểm chạy migration.

Revision ID: w22f0f000022
Revises: v21f0f000021
Create Date: 2026-07-27
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "w22f0f000022"
down_revision = "v21f0f000021"
branch_labels = None
depends_on = None


def _has_table(connection, name: str) -> bool:
    return sa.inspect(connection).has_table(name)


def upgrade() -> None:
    connection = op.get_bind()
    if not _has_table(connection, "users"):
        return
    columns = {c["name"] for c in sa.inspect(connection).get_columns("users")}
    if "password_changed_at" in columns:
        return
    op.execute("ALTER TABLE users ADD COLUMN password_changed_at VARCHAR")
    op.execute("UPDATE users SET password_changed_at = created_at WHERE created_at IS NOT NULL")
    # created_at cũng có thể NULL trên bảng users kiểu cũ (schema T0 không ràng
    # buộc NOT NULL cho cột này) — dùng thời điểm chạy migration làm phương án
    # cuối, thay vì để lại NULL rồi ALTER COLUMN SET NOT NULL thất bại.
    now = datetime.now(timezone.utc).isoformat()
    op.execute(
        sa.text("UPDATE users SET password_changed_at = :now WHERE password_changed_at IS NULL")
        .bindparams(now=now)
    )
    op.execute("ALTER TABLE users ALTER COLUMN password_changed_at SET NOT NULL")


def downgrade() -> None:
    connection = op.get_bind()
    if not _has_table(connection, "users"):
        return
    columns = {c["name"] for c in sa.inspect(connection).get_columns("users")}
    if "password_changed_at" not in columns:
        return
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("password_changed_at")
