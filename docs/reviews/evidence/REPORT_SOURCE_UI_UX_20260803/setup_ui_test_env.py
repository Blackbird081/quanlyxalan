#!/usr/bin/env python
"""Safe Local Test Database Provisioning & Seed Script for quanlyxalan UI/UX Testing.

Usage:
    QLXL_ALLOW_RESET_TEST_DB=1 \
    QLXL_UI_TEST_DATABASE_URL="postgresql+psycopg://<user>:<password>@127.0.0.1:5432/cangvu_ui_test" \
    QLXL_UI_TEST_ADMIN_DATABASE_URL="postgresql+psycopg://<user>:<password>@127.0.0.1:5432/postgres" \
    QLXL_UI_TEST_ADMIN_PASSWORD="<choose-a-local-test-password>" \
    python docs/reviews/evidence/REPORT_SOURCE_UI_UX_20260803/setup_ui_test_env.py

Safety Guards:
  - Requires QLXL_ALLOW_RESET_TEST_DB=1
  - Refuses to drop DB unless both target and admin hosts are local
  - Refuses to drop DB if target database name is not 'cangvu_ui_test'
  - Refuses to run unless the admin connection uses the 'postgres' database
  - Sanitizes all connection credentials in log output
"""
import os
import sys
import re
import json
from pathlib import Path
from urllib.parse import urlparse

# Resolve project root portably
CURRENT_FILE = Path(__file__).resolve()
# Find project root by searching upwards for .cvf or alembic.ini
PROJECT_ROOT = CURRENT_FILE.parent
while PROJECT_ROOT != PROJECT_ROOT.parent and not (PROJECT_ROOT / "alembic.ini").exists():
    PROJECT_ROOT = PROJECT_ROOT.parent

if not (PROJECT_ROOT / "alembic.ini").exists():
    raise RuntimeError(f"Could not locate project root containing alembic.ini from {CURRENT_FILE}")

sys.path.insert(0, str(PROJECT_ROOT))

# Configuration via environment variables with safe fallback defaults for local test environment
TEST_DB_URL = os.getenv("QLXL_UI_TEST_DATABASE_URL", os.getenv("DATABASE_URL", "postgresql+psycopg://127.0.0.1:5432/cangvu_ui_test"))
ADMIN_DB_URL = os.getenv("QLXL_UI_TEST_ADMIN_DATABASE_URL", "postgresql+psycopg://127.0.0.1:5432/postgres")
ADMIN_PASSWORD = os.getenv("QLXL_UI_TEST_ADMIN_PASSWORD")
ALLOW_RESET = os.getenv("QLXL_ALLOW_RESET_TEST_DB", "0")

if not ADMIN_PASSWORD:
    # Fail fast if admin password for seeded user is not provided
    print("[SAFETY GUARD REJECTION] QLXL_UI_TEST_ADMIN_PASSWORD environment variable is required.", file=sys.stderr)
    sys.exit(1)

# Set DATABASE_URL for backend/alembic imports
os.environ["DATABASE_URL"] = TEST_DB_URL


def sanitize_url(url: str) -> str:
    """Mask password credentials in connection URLs for safe logging."""
    return re.sub(r":([^/@]+)@", ":***@", url)


def parse_db_target(url: str) -> tuple[str, str]:
    """Extract host and database name from SQLAlchemy connection URL."""
    # Strip dialect prefix if present (e.g. postgresql+psycopg://)
    clean_url = url.split("://", 1)[-1] if "://" in url else url
    parsed = urlparse(f"//{clean_url}" if not clean_url.startswith("//") else clean_url)
    hostname = (parsed.hostname or "localhost").strip()
    dbname = (parsed.path.lstrip("/") if parsed.path else "").strip()
    return hostname, dbname


def verify_safety_guards():
    """Enforce strict safety controls before dropping or modifying database."""
    if ALLOW_RESET not in ("1", "true", "TRUE", "yes"):
        print("[SAFETY GUARD REJECTION] QLXL_ALLOW_RESET_TEST_DB is not set to 1.", file=sys.stderr)
        print("To allow database reset, set environment variable: QLXL_ALLOW_RESET_TEST_DB=1", file=sys.stderr)
        sys.exit(1)

    host, dbname = parse_db_target(TEST_DB_URL)
    admin_host, admin_dbname = parse_db_target(ADMIN_DB_URL)

    if host not in ("127.0.0.1", "localhost", "::1"):
        print(f"[SAFETY GUARD REJECTION] Target host '{host}' is not a local test host (127.0.0.1/localhost).", file=sys.stderr)
        sys.exit(1)

    if dbname != "cangvu_ui_test":
        print(f"[SAFETY GUARD REJECTION] Target database name '{dbname}' is not 'cangvu_ui_test'.", file=sys.stderr)
        print("This script is strictly restricted to operating on 'cangvu_ui_test'.", file=sys.stderr)
        sys.exit(1)

    if admin_host not in ("127.0.0.1", "localhost", "::1"):
        print(
            f"[SAFETY GUARD REJECTION] Admin host '{admin_host}' is not a local test host "
            "(127.0.0.1/localhost).",
            file=sys.stderr,
        )
        sys.exit(1)

    if admin_dbname != "postgres":
        print(
            f"[SAFETY GUARD REJECTION] Admin database name '{admin_dbname}' is not 'postgres'.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"[SAFETY CHECK PASSED] Target Host={host}, Target DB={dbname}, "
        f"Admin Host={admin_host}, Admin DB={admin_dbname}, Confirmation=ENABLED"
    )


from sqlalchemy import create_engine, text
from backend.database import SessionLocal, now_iso
from backend.auth import get_password_hash
from backend.models import (
    User, Organization, Vessel, Declaration, ReportingUnit,
    ReportingUnitUser, ReportingUnitVessel, ReportingUnitOrganization,
    HistoricalReportImport, HistoricalPortCall, HistoricalCargoRow,
)
from alembic.config import Config
from alembic import command


def seed_database():
    verify_safety_guards()

    print(f"Connecting to admin database: {sanitize_url(ADMIN_DB_URL)}")
    admin_engine = create_engine(ADMIN_DB_URL, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text('DROP DATABASE IF EXISTS "cangvu_ui_test" WITH (FORCE)'))
        conn.execute(text('CREATE DATABASE "cangvu_ui_test"'))
    print(f"Recreated database 'cangvu_ui_test' on host {parse_db_target(TEST_DB_URL)[0]}")

    alembic_ini_path = PROJECT_ROOT / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_DB_URL)
    command.upgrade(alembic_cfg, "head")
    print("Alembic migrations applied successfully.")

    db = SessionLocal()
    try:
        now = now_iso()

        # Reporting Unit
        ru = ReportingUnit(id=1, code="TT", name="Cảng Tân Thuận", created_at=now, updated_at=now)
        db.add(ru)
        db.flush()

        # Organization
        org = Organization(
            id=1, name="Công ty Cổ phần Cảng Tân Thuận", tax_code="0300444555",
            address="Cảng Tân Thuận, Q7, TP.HCM", created_at=now, updated_at=now
        )
        db.add(org)
        db.flush()

        db.add(ReportingUnitOrganization(reporting_unit_id=1, organization_id=1, created_at=now))

        # Platform Admin User
        admin_user = User(
            username="admin",
            password_hash=get_password_hash(ADMIN_PASSWORD),
            full_name="Platform Administrator",
            role="PLATFORM_ADMIN",
            organization_id=None,
            is_active=1,
            created_at=now
        )
        db.add(admin_user)
        db.flush()

        db.add(ReportingUnitUser(reporting_unit_id=1, user_id=admin_user.id, membership_role="ADMIN"))

        # Vessel
        vessel = Vessel(
            id=1,
            organization_id=1,
            name="Sà lan SG-9999",
            registration_no="SG-9999",
            vessel_type="Chở container",
            vessel_class="VR-SI",
            deadweight_tons=1000,
            gross_tonnage=500,
            cargo_capacity_tons=900,
            container_capacity_teu=48,
            min_crew=4,
            safety_certificate_no="ATKT-9999",
            certificate_expiry_date="2027-12-31",
            created_at=now,
            updated_at=now
        )
        db.add(vessel)
        db.flush()

        db.add(ReportingUnitVessel(reporting_unit_id=1, vessel_id=vessel.id, created_at=now))

        cargo_sample = json.dumps({
            "cargo_type": "Container",
            "cargo_name": "Hàng container nhập",
            "movement_type": "Hàng nội địa",
            "tons": 500.0,
            "teu": 30,
            "cont20_full": 10,
            "cont20_empty": 0,
            "cont40_full": 10,
            "cont40_empty": 0
        }, ensure_ascii=False)

        # ----------------------------------------------------
        # SCENARIO 1: LIVE_ONLY (Month 2026-05)
        # ----------------------------------------------------
        decl_may = Declaration(
            reference_no="DECL-202605-001",
            status="APPROVED",
            workflow_status="APPROVED",
            port_approval="APPROVED",
            organization_id=1,
            reporting_unit_id=1,
            vessel_id=1,
            declaration_date="2026-05-10",
            company_name="Công ty Cổ phần Cảng Tân Thuận",
            vessel_name="Sà lan SG-9999",
            registration_no="SG-9999",
            vessel_type="Chở container",
            vessel_class="VR-SI",
            deadweight_tons=1000,
            gross_tonnage=500,
            crew_count=4,
            crew_onboard_count=4,
            last_port="Vũng Tàu",
            working_port="Cảng Tân Thuận",
            departure_berth="K12",
            destination_port="Cần Thơ",
            eta="2026-05-10T08:00:00",
            etd="2026-05-10T16:00:00",
            actual_arrival_at="2026-05-10T08:00:00",
            actual_departure_at="2026-05-10T16:00:00",
            unload_json=cargo_sample,
            load_json="{}",
            master_name="Nguyễn Văn A",
            master_phone="0901234567",
            created_at=now,
            updated_at=now
        )
        db.add(decl_may)

        # ----------------------------------------------------
        # SCENARIO 2: HISTORICAL_ONLY (Month 2026-04)
        # ----------------------------------------------------
        berth_imp_apr = HistoricalReportImport(
            reporting_unit_id=1,
            created_by_user_id=admin_user.id,
            source_kind="tos_berth_call",
            appendix_kind="",
            mapping_version="v1",
            reporting_period="2026-04",
            source_filename="berth_202604.xlsx",
            source_checksum="sha256_apr_berth",
            source_size_bytes=1024,
            status="COMMITTED",
            revision_no=1,
            accepted_count=1,
            created_at=now,
            updated_at=now
        )
        db.add(berth_imp_apr)
        db.flush()

        call_apr = HistoricalPortCall(
            import_id=berth_imp_apr.id,
            reporting_unit_id=1,
            mapping_version="v1",
            vessel_name_raw="Sà lan SG-9999",
            vessel_name_normalized="SA LAN SG 9999",
            call_year_raw="2026",
            voyage_number_raw="0004",
            call_key_normalized="SA LAN SG 9999|2026|0004",
            vessel_id=1,
            arrival_berth="K12",
            departure_berth="K12",
            actual_berthing_at_raw="15/04/2026 08:00:00",
            actual_berthing_at="2026-04-15T08:00:00",
            actual_departure_at_raw="15/04/2026 14:00:00",
            actual_departure_at="2026-04-15T14:00:00",
            reporting_month="2026-04",
            validation_status="VALID",
            created_at=now
        )
        db.add(call_apr)
        db.flush()

        cargo_imp_apr = HistoricalReportImport(
            reporting_unit_id=1,
            created_by_user_id=admin_user.id,
            source_kind="tos_cargo_detail",
            appendix_kind="",
            mapping_version="v1",
            reporting_period="2026-04",
            source_filename="cargo_202604.xlsx",
            source_checksum="sha256_apr_cargo",
            source_size_bytes=1024,
            status="COMMITTED",
            revision_no=1,
            accepted_count=1,
            created_at=now,
            updated_at=now
        )
        db.add(cargo_imp_apr)
        db.flush()

        cargo_apr = HistoricalCargoRow(
            import_id=cargo_imp_apr.id,
            reporting_unit_id=1,
            port_call_id=call_apr.id,
            call_key_normalized="SA LAN SG 9999|2026|0004",
            container_size_code_raw="40HC",
            teu_factor=2,
            full_empty_code_raw="F",
            trade_scope_raw="Hàng nội",
            movement_method_raw="Hạ bãi",
            derived_direction="unload",
            weight_raw="25.0",
            weight_tonnes=25.0,
            weight_state="PRESENT",
            transform_version="v1",
            match_status="MATCHED",
            validation_status="VALID",
            created_at=now
        )
        db.add(cargo_apr)

        # ----------------------------------------------------
        # SCENARIO 3: COMBINED_NON_OVERLAP
        # TOS in 2026-07, LIVE in 2026-08
        # ----------------------------------------------------
        berth_imp_jul = HistoricalReportImport(
            reporting_unit_id=1,
            created_by_user_id=admin_user.id,
            source_kind="tos_berth_call",
            appendix_kind="",
            mapping_version="v1",
            reporting_period="2026-07",
            source_filename="berth_202607.xlsx",
            source_checksum="sha256_jul_berth",
            source_size_bytes=1024,
            status="COMMITTED",
            revision_no=1,
            accepted_count=2,
            created_at=now,
            updated_at=now
        )
        db.add(berth_imp_jul)
        db.flush()

        # Call 1 (Voyage 0007-A)
        call_jul_1 = HistoricalPortCall(
            import_id=berth_imp_jul.id,
            reporting_unit_id=1,
            source_row=1,
            mapping_version="v1",
            vessel_name_raw="Sà lan SG-9999",
            vessel_name_normalized="SA LAN SG 9999",
            call_year_raw="2026",
            voyage_number_raw="0007",
            call_key_normalized="SA LAN SG 9999|2026|0007",
            vessel_id=1,
            arrival_berth="K12",
            departure_berth="K12",
            actual_berthing_at_raw="10/07/2026 08:00:00",
            actual_berthing_at="2026-07-10T08:00:00",
            actual_departure_at_raw="10/07/2026 14:00:00",
            actual_departure_at="2026-07-10T14:00:00",
            reporting_month="2026-07",
            validation_status="VALID",
            created_at=now
        )
        # Call 2 (Voyage 0008-B - Same Salan, separate voyage in same month)
        call_jul_2 = HistoricalPortCall(
            import_id=berth_imp_jul.id,
            reporting_unit_id=1,
            source_row=2,
            mapping_version="v1",
            vessel_name_raw="Sà lan SG-9999",
            vessel_name_normalized="SA LAN SG 9999",
            call_year_raw="2026",
            voyage_number_raw="0008",
            call_key_normalized="SA LAN SG 9999|2026|0008",
            vessel_id=1,
            arrival_berth="K13",
            departure_berth="K13",
            actual_berthing_at_raw="22/07/2026 09:00:00",
            actual_berthing_at="2026-07-22T09:00:00",
            actual_departure_at_raw="22/07/2026 18:00:00",
            actual_departure_at="2026-07-22T18:00:00",
            reporting_month="2026-07",
            validation_status="VALID",
            created_at=now
        )
        db.add_all([call_jul_1, call_jul_2])
        db.flush()

        cargo_imp_jul = HistoricalReportImport(
            reporting_unit_id=1,
            created_by_user_id=admin_user.id,
            source_kind="tos_cargo_detail",
            appendix_kind="",
            mapping_version="v1",
            reporting_period="2026-07",
            source_filename="cargo_202607.xlsx",
            source_checksum="sha256_jul_cargo",
            source_size_bytes=1024,
            status="COMMITTED",
            revision_no=1,
            accepted_count=2,
            created_at=now,
            updated_at=now
        )
        db.add(cargo_imp_jul)
        db.flush()

        cargo_jul_1 = HistoricalCargoRow(
            import_id=cargo_imp_jul.id,
            reporting_unit_id=1,
            source_row=1,
            port_call_id=call_jul_1.id,
            call_key_normalized="SA LAN SG 9999|2026|0007",
            container_size_code_raw="20GP",
            teu_factor=1,
            full_empty_code_raw="F",
            trade_scope_raw="Hàng nội",
            movement_method_raw="Hạ bãi",
            derived_direction="unload",
            weight_raw="12.0",
            weight_tonnes=12.0,
            weight_state="PRESENT",
            transform_version="v1",
            match_status="MATCHED",
            validation_status="VALID",
            created_at=now
        )
        cargo_jul_2 = HistoricalCargoRow(
            import_id=cargo_imp_jul.id,
            reporting_unit_id=1,
            source_row=2,
            port_call_id=call_jul_2.id,
            call_key_normalized="SA LAN SG 9999|2026|0008",
            container_size_code_raw="40HC",
            teu_factor=2,
            full_empty_code_raw="F",
            trade_scope_raw="Hàng nội",
            movement_method_raw="Hạ bãi",
            derived_direction="unload",
            weight_raw="28.0",
            weight_tonnes=28.0,
            weight_state="PRESENT",
            transform_version="v1",
            match_status="MATCHED",
            validation_status="VALID",
            created_at=now
        )
        db.add_all([cargo_jul_1, cargo_jul_2])

        decl_aug = Declaration(
            reference_no="DECL-202608-001",
            status="APPROVED",
            workflow_status="APPROVED",
            port_approval="APPROVED",
            organization_id=1,
            reporting_unit_id=1,
            vessel_id=1,
            declaration_date="2026-08-10",
            company_name="Công ty Cổ phần Cảng Tân Thuận",
            vessel_name="Sà lan SG-9999",
            registration_no="SG-9999",
            vessel_type="Chở container",
            vessel_class="VR-SI",
            deadweight_tons=1000,
            gross_tonnage=500,
            crew_count=4,
            crew_onboard_count=4,
            last_port="Vũng Tàu",
            working_port="Cảng Tân Thuận",
            departure_berth="K12",
            destination_port="Cần Thơ",
            eta="2026-08-10T08:00:00",
            etd="2026-08-10T16:00:00",
            actual_arrival_at="2026-08-10T08:00:00",
            actual_departure_at="2026-08-10T16:00:00",
            unload_json=cargo_sample,
            load_json="{}",
            master_name="Nguyễn Văn B",
            master_phone="0908888888",
            created_at=now,
            updated_at=now
        )
        db.add(decl_aug)

        # ----------------------------------------------------
        # SCENARIO 4: COMBINED_OVERLAP (Month 2026-07)
        # TOS in 2026-07 AND LIVE in 2026-07
        # ----------------------------------------------------
        decl_jul = Declaration(
            reference_no="DECL-202607-001",
            status="APPROVED",
            workflow_status="APPROVED",
            port_approval="APPROVED",
            organization_id=1,
            reporting_unit_id=1,
            vessel_id=1,
            declaration_date="2026-07-20",
            company_name="Công ty Cổ phần Cảng Tân Thuận",
            vessel_name="Sà lan SG-9999",
            registration_no="SG-9999",
            vessel_type="Chở container",
            vessel_class="VR-SI",
            deadweight_tons=1000,
            gross_tonnage=500,
            crew_count=4,
            crew_onboard_count=4,
            last_port="Vũng Tàu",
            working_port="Cảng Tân Thuận",
            departure_berth="K12",
            destination_port="Cần Thơ",
            eta="2026-07-20T08:00:00",
            etd="2026-07-20T16:00:00",
            actual_arrival_at="2026-07-20T08:00:00",
            actual_departure_at="2026-07-20T16:00:00",
            unload_json=cargo_sample,
            load_json="{}",
            master_name="Nguyễn Văn C",
            master_phone="0909999999",
            created_at=now,
            updated_at=now
        )
        db.add(decl_jul)

        db.commit()
        print("Data seeded successfully for all 4 scenarios in cangvu_ui_test!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
