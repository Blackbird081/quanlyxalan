"""scope historical import idempotency to reporting period

Revision ID: y24f0f000024
Revises: x23f0f000023
Create Date: 2026-07-29
"""
from alembic import op
import sqlalchemy as sa


revision = "y24f0f000024"
down_revision = "x23f0f000023"
branch_labels = None
depends_on = None


CONSTRAINT_NAME = "uq_historical_import_idempotency"
OLD_COLUMNS = [
    "reporting_unit_id",
    "source_kind",
    "source_checksum",
    "mapping_version",
]
NEW_COLUMNS = [*OLD_COLUMNS, "reporting_period"]


def _unique_columns(inspector: sa.Inspector) -> tuple[str, ...] | None:
    for constraint in inspector.get_unique_constraints("historical_report_imports"):
        if constraint["name"] == CONSTRAINT_NAME:
            return tuple(constraint.get("column_names") or ())
    return None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if "historical_report_imports" not in inspector.get_table_names():
        return
    if _unique_columns(inspector) == tuple(NEW_COLUMNS):
        return
    with op.batch_alter_table("historical_report_imports") as batch:
        if _unique_columns(inspector) is not None:
            batch.drop_constraint(CONSTRAINT_NAME, type_="unique")
        batch.create_unique_constraint(
            CONSTRAINT_NAME,
            NEW_COLUMNS,
            postgresql_nulls_not_distinct=True,
        )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if "historical_report_imports" not in inspector.get_table_names():
        return
    period_distinct_duplicates = connection.execute(sa.text("""
        SELECT COUNT(*) FROM (
            SELECT reporting_unit_id, source_kind, source_checksum, mapping_version
            FROM historical_report_imports
            GROUP BY reporting_unit_id, source_kind, source_checksum, mapping_version
            HAVING COUNT(*) > 1
        ) AS duplicates
    """)).scalar_one()
    if period_distinct_duplicates:
        raise RuntimeError(
            "Refusing downgrade: period-scoped historical imports cannot be "
            "represented by the pre-y24 idempotency constraint."
        )
    with op.batch_alter_table("historical_report_imports") as batch:
        if _unique_columns(inspector) is not None:
            batch.drop_constraint(CONSTRAINT_NAME, type_="unique")
        batch.create_unique_constraint(CONSTRAINT_NAME, OLD_COLUMNS)
