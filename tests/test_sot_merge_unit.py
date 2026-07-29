from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from backend.database import now_iso
from backend.historical_api import _filter_confirmed_sot_rows
from backend.historical_tos_parser import ParsedWorkbook, normalize_vessel_name
from backend.models import (
    Attachment,
    Base,
    HistoricalCargoRow,
    HistoricalPortCall,
    HistoricalReportImport,
    HistoricalReportRow,
    ReportingUnit,
    User,
)
from backend.storage import LocalQuarantineStorage


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _unit_and_user(db):
    unit = ReportingUnit(
        name="SOT test port", code="SOT", is_active=1,
        created_at=now_iso(), updated_at=now_iso(),
    )
    user = User(
        username="sot-admin", password_hash="x", role="PLATFORM_ADMIN",
        is_active=1, created_at=now_iso(), password_changed_at=now_iso(),
    )
    db.add_all([unit, user])
    db.commit()
    return unit, user


def _active_import(db, unit, user, source_kind, checksum):
    item = HistoricalReportImport(
        reporting_unit_id=unit.id,
        source_kind=source_kind,
        appendix_kind="PL.03" if source_kind == "reported_pl03" else "",
        mapping_version="unit-test-v1",
        source_filename="source.xlsx",
        source_checksum=checksum,
        source_size_bytes=1,
        status="COMMITTED",
        created_by_user_id=user.id,
        created_at=now_iso(),
        updated_at=now_iso(),
    )
    db.add(item)
    db.commit()
    return item


def test_confirmed_berth_call_is_retained_and_only_new_call_is_staged(db):
    unit, user = _unit_and_user(db)
    item = _active_import(db, unit, user, "tos_berth_call", "berth")
    db.add(HistoricalPortCall(
        reporting_unit_id=unit.id,
        import_id=item.id,
        source_sheet="S",
        source_row=2,
        mapping_version="unit-test-v1",
        call_key_normalized="SALANA|2092|1",
        validation_status="VALID",
        created_at=now_iso(),
    ))
    db.commit()
    parsed = ParsedWorkbook(
        source_kind="tos_berth_call",
        mapping_version="unit-test-v1",
        rows=[
            {"call_key_normalized": "SALANA|2092|1"},
            {"call_key_normalized": "SALANB|2092|2"},
        ],
    )

    new_rows, retained, import_ids = _filter_confirmed_sot_rows(
        db, unit_id=unit.id, parsed=parsed,
    )

    assert new_rows == [{"call_key_normalized": "SALANB|2092|2"}]
    assert retained == 1
    assert import_ids == [item.id]


def test_cargo_sot_matching_preserves_duplicate_multiplicity(db):
    unit, user = _unit_and_user(db)
    item = _active_import(db, unit, user, "tos_cargo_detail", "cargo")
    common = dict(
        reporting_unit_id=unit.id,
        import_id=item.id,
        source_sheet="S",
        call_key_normalized="SALANA|2092|1",
        container_size_code_raw="20GP",
        full_empty_code_raw="F",
        trade_scope_raw="Hàng nội",
        movement_method_raw="Hạ bãi",
        derived_direction="unload",
        weight_raw="10.5",
        weight_tonnes=10.5,
        weight_state="PRESENT",
        transform_version="unit-test-v1",
        validation_status="VALID",
        created_at=now_iso(),
    )
    db.add_all([
        HistoricalCargoRow(source_row=2, **common),
        HistoricalCargoRow(source_row=3, **common),
    ])
    db.commit()
    source = {
        "call_key_normalized": "SALANA|2092|1",
        "container_size_code_raw": "20GP",
        "full_empty_code_raw": "F",
        "trade_scope_raw": "Hàng nội",
        "movement_method_raw": "Hạ bãi",
        "derived_direction": "unload",
        "weight_raw": "10.5",
        "weight_tonnes": 10.5,
        "weight_state": "PRESENT",
    }
    new_fact = {**source, "weight_raw": "11", "weight_tonnes": 11.0}
    parsed = ParsedWorkbook(
        source_kind="tos_cargo_detail",
        mapping_version="unit-test-v1",
        rows=[source.copy(), source.copy(), source.copy(), new_fact],
    )

    new_rows, retained, import_ids = _filter_confirmed_sot_rows(
        db, unit_id=unit.id, parsed=parsed,
    )

    assert retained == 2
    assert new_rows == [source, new_fact]
    assert import_ids == [item.id]


def test_pl03_registration_identity_keeps_confirmed_row_even_if_file_value_changes(db):
    unit, user = _unit_and_user(db)
    item = _active_import(db, unit, user, "reported_pl03", "pl03")
    db.add(HistoricalReportRow(
        reporting_unit_id=unit.id,
        import_id=item.id,
        source_sheet="S",
        source_row=10,
        normalized_registration=normalize_vessel_name("SG-001"),
        mapped_dimensions_json='{"vesselNameRaw":"SALAN A"}',
        validation_status="VALID",
        created_at=now_iso(),
    ))
    db.commit()
    parsed = ParsedWorkbook(
        source_kind="reported_pl03",
        mapping_version="unit-test-v1",
        rows=[
            {"registration_raw": "SG-001", "vessel_name_raw": "CHANGED"},
            {"registration_raw": "SG-002", "vessel_name_raw": "SALAN B"},
        ],
    )

    new_rows, retained, import_ids = _filter_confirmed_sot_rows(
        db, unit_id=unit.id, parsed=parsed,
    )

    assert retained == 1
    assert new_rows == [{"registration_raw": "SG-002", "vessel_name_raw": "SALAN B"}]
    assert import_ids == [item.id]


def test_attachment_requires_exactly_one_owner(db):
    db.add(Attachment(
        original_name="invalid.pdf",
        stored_name="invalid.pdf",
        content_type="application/pdf",
        size_bytes=1,
        checksum_sha256="x",
        scan_status="QUARANTINED",
        storage_backend="LOCAL_QUARANTINE",
        created_at=now_iso(),
    ))
    with pytest.raises(IntegrityError):
        db.commit()


def test_local_quarantine_storage_deletes_only_inside_root(tmp_path: Path):
    storage = LocalQuarantineStorage(tmp_path / "quarantine")
    key = storage.put_quarantined("vessel_1.pdf", b"%PDF")
    target = storage.root / key
    assert target.exists()
    storage.delete(key)
    assert not target.exists()
    with pytest.raises(ValueError):
        storage.delete("../outside.pdf")
