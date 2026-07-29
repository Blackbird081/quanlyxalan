"""allow quarantined attachments to belong to a vessel

Revision ID: x23f0f000023
Revises: w22f0f000022
Create Date: 2026-07-29
"""
from alembic import op
import sqlalchemy as sa


revision = "x23f0f000023"
down_revision = "w22f0f000022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if "attachments" not in inspector.get_table_names():
        return
    columns = {column["name"]: column for column in inspector.get_columns("attachments")}
    checks = {constraint["name"] for constraint in inspector.get_check_constraints("attachments")}
    foreign_keys = {constraint["name"] for constraint in inspector.get_foreign_keys("attachments")}
    with op.batch_alter_table("attachments") as batch:
        if "vessel_id" not in columns:
            batch.add_column(sa.Column("vessel_id", sa.Integer(), nullable=True))
        if not columns["declaration_id"]["nullable"]:
            batch.alter_column("declaration_id", existing_type=sa.Integer(), nullable=True)
        if "fk_attachments_vessel_id_vessels" not in foreign_keys:
            batch.create_foreign_key(
                "fk_attachments_vessel_id_vessels",
                "vessels",
                ["vessel_id"],
                ["id"],
                ondelete="CASCADE",
            )
        if "ck_attachments_exactly_one_owner" not in checks:
            batch.create_check_constraint(
                "ck_attachments_exactly_one_owner",
                "(declaration_id IS NOT NULL AND vessel_id IS NULL) OR "
                "(declaration_id IS NULL AND vessel_id IS NOT NULL)",
            )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if "attachments" not in inspector.get_table_names():
        return
    columns = {column["name"]: column for column in inspector.get_columns("attachments")}
    if "vessel_id" not in columns:
        return
    vessel_attachment_count = connection.execute(
        sa.text("SELECT COUNT(*) FROM attachments WHERE vessel_id IS NOT NULL")
    ).scalar_one()
    if vessel_attachment_count:
        raise RuntimeError(
            "Refusing downgrade: vessel attachments exist and cannot be represented by w22."
        )
    checks = {constraint["name"] for constraint in inspector.get_check_constraints("attachments")}
    foreign_keys = {constraint["name"] for constraint in inspector.get_foreign_keys("attachments")}
    with op.batch_alter_table("attachments") as batch:
        if "ck_attachments_exactly_one_owner" in checks:
            batch.drop_constraint("ck_attachments_exactly_one_owner", type_="check")
        if "fk_attachments_vessel_id_vessels" in foreign_keys:
            batch.drop_constraint("fk_attachments_vessel_id_vessels", type_="foreignkey")
        batch.drop_column("vessel_id")
        batch.alter_column("declaration_id", existing_type=sa.Integer(), nullable=False)
