from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from backend.database import now_iso
from backend.historical_api import (
    _accepted_vessel_sot, _conflicts, _filter_confirmed_sot_rows,
    _reconcile_pending_vessel_sot, _vessel_sot_resolution,
)
from backend.historical_tos_parser import ParsedWorkbook, normalize_vessel_name
from backend.models import (
    Attachment,
    Base,
    HistoricalCargoRow,
    HistoricalPortCall,
    HistoricalReportImport,
    HistoricalReportRow,
    HistoricalVesselLink,
    ReportingUnit,
    ReportingUnitVessel,
    User,
    Vessel,
)
from backend.storage import LocalQuarantineStorage


def test_unique_normalized_register_match_is_accepted_as_admin_sot():
    vessel = type("VesselStub", (), {"id": 7, "name": "KIM GIA PHÁT 01"})()

    candidate, method, confidence, warning, auto_accept = _vessel_sot_resolution(
        [vessel], {vessel.id: vessel}, {}, "KIM GIA PHAT 01",
    )

    assert candidate.id == vessel.id
    assert method == "NORMALIZED"
    assert confidence == "MEDIUM"
    assert warning == ""
    assert auto_accept is True


def test_latest_admin_rejection_keeps_alias_pending():
    vessel = type("VesselStub", (), {"id": 7, "name": "CANONICAL A"})()

    candidate, method, confidence, warning, auto_accept = _vessel_sot_resolution(
        [vessel],
        {vessel.id: vessel},
        {"TOSALIAS": None},
        "TOS ALIAS",
    )

    assert candidate is None
    assert method == ""
    assert confidence == "LOW"
    assert warning == "UNMATCHED_VESSEL"
    assert auto_accept is False


def test_latest_admin_accepted_mapping_becomes_current_sot(db):
    unit, user = _unit_and_user(db)
    vessels = [
        Vessel(
            name="CANONICAL A", registration_no="SOT-A", vessel_type="Salan",
            vessel_class="VR-SI", created_at=now_iso(), updated_at=now_iso(),
        ),
        Vessel(
            name="CANONICAL B", registration_no="SOT-B", vessel_type="Salan",
            vessel_class="VR-SI", created_at=now_iso(), updated_at=now_iso(),
        ),
    ]
    db.add_all(vessels)
    db.flush()
    db.add_all([
        ReportingUnitVessel(
            reporting_unit_id=unit.id, vessel_id=vessel.id, created_at=now_iso(),
        )
        for vessel in vessels
    ])
    imports = [
        _active_import(db, unit, user, "tos_berth_call", "older"),
        _active_import(db, unit, user, "tos_berth_call", "newer"),
    ]
    db.add_all([
        HistoricalVesselLink(
            reporting_unit_id=unit.id, import_id=imports[0].id,
            raw_vessel_name="TOS ALIAS", normalized_vessel_name="TOSALIAS",
            candidate_vessel_id=vessels[0].id, match_method="MANUAL",
            confidence="HIGH", link_status="ACCEPTED",
            reviewed_by_user_id=user.id, reviewed_at="2026-07-29T10:00:00+00:00",
            created_at="2026-07-29T09:00:00+00:00",
        ),
        HistoricalVesselLink(
            reporting_unit_id=unit.id, import_id=imports[1].id,
            raw_vessel_name="TOS ALIAS", normalized_vessel_name="TOSALIAS",
            candidate_vessel_id=vessels[1].id, match_method="MANUAL",
            confidence="HIGH", link_status="ACCEPTED",
            reviewed_by_user_id=user.id, reviewed_at="2026-07-30T10:00:00+00:00",
            created_at="2026-07-30T09:00:00+00:00",
        ),
    ])
    db.commit()

    accepted = _accepted_vessel_sot(
        db, unit.id, {vessels[0].id, vessels[1].id},
    )

    assert accepted == {"TOSALIAS": vessels[1].id}


def test_port_staff_acceptance_does_not_seed_admin_sot(db):
    unit, admin = _unit_and_user(db)
    port_staff = User(
        username="sot-port-staff", password_hash="x", role="PORT_STAFF",
        is_active=1, created_at=now_iso(), password_changed_at=now_iso(),
    )
    vessel = Vessel(
        name="CANONICAL STAFF", registration_no="SOT-STAFF",
        vessel_type="Salan", vessel_class="VR-SI",
        created_at=now_iso(), updated_at=now_iso(),
    )
    db.add_all([port_staff, vessel])
    db.flush()
    db.add(ReportingUnitVessel(
        reporting_unit_id=unit.id, vessel_id=vessel.id, created_at=now_iso(),
    ))
    item = _active_import(db, unit, admin, "tos_berth_call", "staff-decision")
    db.add(HistoricalVesselLink(
        reporting_unit_id=unit.id, import_id=item.id,
        raw_vessel_name="STAFF ALIAS", normalized_vessel_name="STAFFALIAS",
        candidate_vessel_id=vessel.id, match_method="MANUAL",
        confidence="HIGH", link_status="ACCEPTED",
        reviewed_by_user_id=port_staff.id,
        reviewed_at="2026-07-30T10:00:00+00:00", created_at=now_iso(),
    ))
    db.commit()

    assert _accepted_vessel_sot(db, unit.id, {vessel.id}) == {}


def test_latest_admin_rejection_tombstones_older_acceptance(db):
    unit, admin = _unit_and_user(db)
    vessel = Vessel(
        name="CANONICAL REJECT", registration_no="SOT-REJECT",
        vessel_type="Salan", vessel_class="VR-SI",
        created_at=now_iso(), updated_at=now_iso(),
    )
    db.add(vessel)
    db.flush()
    db.add(ReportingUnitVessel(
        reporting_unit_id=unit.id, vessel_id=vessel.id, created_at=now_iso(),
    ))
    imports = [
        _active_import(db, unit, admin, "tos_berth_call", "accepted-before-reject"),
        _active_import(db, unit, admin, "tos_berth_call", "latest-reject"),
    ]
    db.add_all([
        HistoricalVesselLink(
            reporting_unit_id=unit.id, import_id=imports[0].id,
            raw_vessel_name="REJECTED ALIAS", normalized_vessel_name="REJECTEDALIAS",
            candidate_vessel_id=vessel.id, match_method="MANUAL",
            confidence="HIGH", link_status="ACCEPTED",
            reviewed_by_user_id=admin.id,
            reviewed_at="2026-07-29T10:00:00+00:00", created_at=now_iso(),
        ),
        HistoricalVesselLink(
            reporting_unit_id=unit.id, import_id=imports[1].id,
            raw_vessel_name="REJECTED ALIAS", normalized_vessel_name="REJECTEDALIAS",
            candidate_vessel_id=vessel.id, match_method="MANUAL",
            confidence="HIGH", link_status="REJECTED",
            reviewed_by_user_id=admin.id,
            reviewed_at="2026-07-30T10:00:00+00:00", created_at=now_iso(),
        ),
    ])
    db.commit()

    assert _accepted_vessel_sot(
        db, unit.id, {vessel.id},
    ) == {"REJECTEDALIAS": None}


def test_admin_triggered_auto_reconcile_does_not_seed_manual_alias_sot(db):
    unit, admin = _unit_and_user(db)
    vessel = Vessel(
        name="KIM GIA PHÁT 01", registration_no="SOT-AUTO",
        vessel_type="Salan", vessel_class="VR-SI",
        created_at=now_iso(), updated_at=now_iso(),
    )
    db.add(vessel)
    db.flush()
    db.add(ReportingUnitVessel(
        reporting_unit_id=unit.id, vessel_id=vessel.id, created_at=now_iso(),
    ))
    item = HistoricalReportImport(
        reporting_unit_id=unit.id, source_kind="tos_berth_call",
        appendix_kind="", mapping_version="unit-test-v1",
        source_filename="auto-reconcile.xlsx", source_checksum="auto-reconcile",
        source_size_bytes=1, status="PREVIEWED", created_by_user_id=admin.id,
        created_at=now_iso(), updated_at=now_iso(),
    )
    db.add(item)
    db.flush()
    link = HistoricalVesselLink(
        reporting_unit_id=unit.id, import_id=item.id,
        raw_vessel_name="KIM GIA PHAT 01",
        normalized_vessel_name=normalize_vessel_name("KIM GIA PHAT 01"),
        candidate_vessel_id=vessel.id, match_method="NORMALIZED",
        confidence="MEDIUM", link_status="PENDING",
        reason="REVIEW_NORMALIZED_VESSEL_LINK", created_at=now_iso(),
    )
    db.add(link)
    db.commit()

    assert _reconcile_pending_vessel_sot(
        db, unit.id, admin.id, import_ids={item.id},
    ) == [item.id]
    db.commit()
    db.refresh(link)
    assert link.link_status == "ACCEPTED"
    assert link.reviewed_by_user_id is None
    assert link.reviewed_at is None

    item.status = "COMMITTED"
    vessel.name = "RENAMED TO DIFFERENT IDENTITY"
    db.commit()

    registered = {vessel.id}
    assert _accepted_vessel_sot(db, unit.id, registered) == {}
    candidate, _, _, warning, auto_accept = _vessel_sot_resolution(
        [vessel], {vessel.id: vessel}, {}, "KIM GIA PHAT 01",
    )
    assert candidate is None
    assert warning == "UNMATCHED_VESSEL"
    assert auto_accept is False


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


def _active_import(db, unit, user, source_kind, checksum, reporting_period=None):
    item = HistoricalReportImport(
        reporting_unit_id=unit.id,
        source_kind=source_kind,
        appendix_kind="PL.03" if source_kind == "reported_pl03" else "",
        mapping_version="unit-test-v1",
        reporting_period=reporting_period,
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
    item = _active_import(
        db, unit, user, "reported_pl03", "pl03", reporting_period="2092-07",
    )
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
        reporting_period="2092-07",
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


def test_pl03_same_vessel_in_different_period_is_a_new_fact(db):
    unit, user = _unit_and_user(db)
    item = _active_import(
        db, unit, user, "reported_pl03", "pl03-july", reporting_period="2092-07",
    )
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
    source = {"registration_raw": "SG-001", "vessel_name_raw": "SALAN A"}
    parsed = ParsedWorkbook(
        source_kind="reported_pl03",
        mapping_version="unit-test-v1",
        reporting_period="2092-08",
        rows=[source],
    )

    new_rows, retained, import_ids = _filter_confirmed_sot_rows(
        db, unit_id=unit.id, parsed=parsed,
    )

    assert new_rows == [source]
    assert retained == 0
    assert import_ids == []


def test_pl03_same_checksum_in_different_period_is_not_a_conflict(db):
    unit, user = _unit_and_user(db)
    _active_import(
        db, unit, user, "reported_pl03", "same-checksum", reporting_period="2092-07",
    )
    august = HistoricalReportImport(
        reporting_unit_id=unit.id,
        source_kind="reported_pl03",
        appendix_kind="PL.03",
        mapping_version="unit-test-v1",
        reporting_period="2092-08",
        source_filename="source.xlsx",
        source_checksum="same-checksum",
        source_size_bytes=1,
        status="PREVIEWED",
        created_by_user_id=user.id,
        created_at=now_iso(),
        updated_at=now_iso(),
    )
    db.add(august)
    db.commit()

    assert _conflicts(db, august) == []


def test_full_revision_conflict_set_contains_all_active_receipts_in_period(db):
    unit, user = _unit_and_user(db)
    first = _active_import(
        db, unit, user, "reported_pl03", "first", reporting_period="2092-07",
    )
    second = _active_import(
        db, unit, user, "reported_pl03", "second", reporting_period="2092-07",
    )
    revision = HistoricalReportImport(
        reporting_unit_id=unit.id,
        source_kind="reported_pl03",
        appendix_kind="PL.03",
        mapping_version="unit-test-v1",
        reporting_period="2092-07",
        source_filename="revision.xlsx",
        source_checksum="revision",
        source_size_bytes=1,
        status="PREVIEWED",
        created_by_user_id=user.id,
        created_at=now_iso(),
        updated_at=now_iso(),
    )
    db.add(revision)
    db.commit()

    assert [item.id for item in _conflicts(db, revision)] == [first.id, second.id]


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
