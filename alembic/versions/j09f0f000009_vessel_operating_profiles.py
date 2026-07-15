"""preserve vessel operating profiles and port tracking contacts

Revision ID: j09f0f000009
Revises: i08f0f000008
Create Date: 2026-07-15
"""
from alembic import op
import sqlalchemy as sa
import re


revision = "j09f0f000009"
down_revision = "i08f0f000008"
branch_labels = None
depends_on = None


def _numbers(value: str) -> list[float]:
    result = []
    for token in re.findall(r"[-+]?\d[\d.,]*", value or ""):
        token = token.rstrip(".,")
        if "," in token and "." in token:
            token = token.replace(".", "").replace(",", ".") if token.rfind(",") > token.rfind(".") else token.replace(",", "")
        elif "," in token:
            token = token.replace(",", ".")
        try:
            result.append(float(token))
        except ValueError:
            pass
    return result


def _noted_values(notes: str, field: str, fallback: float | None) -> list[float | None]:
    match = re.search(rf"{re.escape(field)}=([^;|]+)", notes or "")
    values = _numbers(match.group(1)) if match else []
    return values or [fallback]


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    vessel_columns = {column["name"] for column in inspector.get_columns("vessels")}
    with op.batch_alter_table("vessels") as batch:
        if "tracking_master_name" not in vessel_columns:
            batch.add_column(sa.Column("tracking_master_name", sa.String(), nullable=False, server_default=""))
        if "tracking_master_phone" not in vessel_columns:
            batch.add_column(sa.Column("tracking_master_phone", sa.String(), nullable=False, server_default=""))
    profile_table_created = "vessel_operating_profiles" not in inspector.get_table_names()
    if profile_table_created:
        op.create_table(
            "vessel_operating_profiles",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("vessel_id", sa.Integer(), sa.ForeignKey("vessels.id", ondelete="CASCADE"), nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("activity_area", sa.String(), nullable=False, server_default=""),
            sa.Column("deadweight_tons", sa.Float()),
            sa.Column("cargo_capacity_tons", sa.Float()),
        )
    if not profile_table_created:
        return
    rows = connection.execute(sa.text(
        "SELECT id, vessel_class, deadweight_tons, cargo_capacity_tons, notes FROM vessels"
    )).mappings()
    for row in rows:
        areas = [part.strip() for part in re.split(r"\s*/\s*", row["vessel_class"] or "") if part.strip()]
        deadweights = _noted_values(row["notes"] or "", "deadweight_tons", row["deadweight_tons"])
        capacities = _noted_values(row["notes"] or "", "cargo_capacity_tons", row["cargo_capacity_tons"])
        count = max(len(areas), len(deadweights), len(capacities), 1)
        for index in range(count):
            connection.execute(sa.text(
                "INSERT INTO vessel_operating_profiles "
                "(vessel_id, sequence, activity_area, deadweight_tons, cargo_capacity_tons) "
                "VALUES (:vessel_id, :sequence, :activity_area, :deadweight, :capacity)"
            ), {
                "vessel_id": row["id"],
                "sequence": index + 1,
                "activity_area": areas[index] if index < len(areas) else "",
                "deadweight": deadweights[index] if index < len(deadweights) else None,
                "capacity": capacities[index] if index < len(capacities) else None,
            })


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if "vessel_operating_profiles" in inspector.get_table_names():
        op.drop_table("vessel_operating_profiles")
    vessel_columns = {column["name"] for column in sa.inspect(connection).get_columns("vessels")}
    with op.batch_alter_table("vessels") as batch:
        if "tracking_master_phone" in vessel_columns:
            batch.drop_column("tracking_master_phone")
        if "tracking_master_name" in vessel_columns:
            batch.drop_column("tracking_master_name")
