"""Tenant-scoped preview/confirm API for historical TOS and PL.03 sources."""
from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter, OrderedDict
from datetime import date
from pathlib import Path
from typing import Any, Literal
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from .database import audit, get_db, now_iso
from .historical import (
    HistoricalAuthorizationError, HistoricalTenantError, validate_import_actor,
    validate_reviewer, validate_vessel_link_tenant,
)
from .historical_tos_parser import (
    HistoricalWorkbookError, ParsedWorkbook, TRANSFORM_VERSION, json_dumps,
    normalize_token, normalize_vessel_name, parse_workbook,
)
from .models import (
    HistoricalCargoRow, HistoricalPortCall, HistoricalReportImport,
    HistoricalReportMetric, HistoricalReportRow, HistoricalVesselLink,
    ReportingUnit, ReportingUnitVessel, Vessel,
)
from .tenant import Scope, require_port_scope
from .xlsx_io import make_report_xlsx


router = APIRouter(prefix="/api/historical-imports", tags=["historical-imports"])
MAX_SOURCE_BYTES = 12 * 1024 * 1024
ACTIVE_IMPORT_STATUSES = ("COMMITTED", "REVIEW")
ROOT = Path(__file__).resolve().parents[1]
SOURCE_ARCHIVE_ROOT = Path(os.environ.get("HISTORICAL_SOURCE_DIR", ROOT / "data" / "historical_sources"))


class ConfirmHistoricalImport(BaseModel):
    conflict_action: Literal[
        "KEEP_EXISTING", "MERGE_NEW_RECORDS", "ACTIVATE_NEW_REVISION",
    ] | None = None
    reason: str = Field(default="", max_length=500)
    supersedes_import_id: int | None = None


class ResolveVesselLink(BaseModel):
    decision: Literal["ACCEPT", "REJECT"]
    candidate_vessel_id: int | None = None
    reason: str = Field(default="", max_length=500)


class CancelHistoricalImport(BaseModel):
    reason: str = Field(default="Người dùng hủy sau khi xem preview.", max_length=500)


def _authorize(db: Session, scope: Scope, *, reviewer: bool = False) -> None:
    try:
        validator = validate_reviewer if reviewer else validate_import_actor
        key = "reviewer" if reviewer else "user"
        validator(
            db, reporting_unit_id=scope.reporting_unit_id,
            platform_context=scope.user.role == "PLATFORM_ADMIN", **{key: scope.user},
        )
    except HistoricalAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _source_filename(value: str | None) -> str:
    if not value:
        return "uploaded.xlsx"
    cleaned = Path(unquote(value).replace("\\", "/")).name.strip()
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", cleaned)[:255]
    return cleaned or "uploaded.xlsx"


def _archive_source(reporting_unit_id: int, checksum: str, content: bytes) -> str:
    directory = SOURCE_ARCHIVE_ROOT / str(reporting_unit_id)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{checksum}.xlsx"
    if not target.exists():
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(content)
        os.replace(temporary, target)
    return str(target.relative_to(SOURCE_ARCHIVE_ROOT)).replace("\\", "/")


def _mapping_receipt(item: HistoricalReportImport) -> dict[str, Any]:
    try:
        return json.loads(item.mapping_receipt_json or "{}")
    except (TypeError, ValueError):
        return {}


def _import_json(item: HistoricalReportImport, *, conflicts: list[int] | None = None) -> dict[str, Any]:
    receipt = _mapping_receipt(item)
    return {
        "id": item.id, "reportingUnitId": item.reporting_unit_id,
        "sourceKind": item.source_kind, "appendixKind": item.appendix_kind,
        "mappingVersion": item.mapping_version, "reportingPeriod": item.reporting_period,
        "sourceFilename": item.source_filename, "checksum": item.source_checksum,
        "sourceSizeBytes": item.source_size_bytes, "status": item.status,
        "revisionNo": item.revision_no, "supersededByImportId": item.superseded_by_import_id,
        "accepted": item.accepted_count, "review": item.review_count,
        "rejected": item.rejected_count, "createdAt": item.created_at,
        "conflictingImportIds": conflicts or [],
        "sotRetainedCount": int(receipt.get("sotRetainedCount") or 0),
        "newRowCount": int(receipt.get("newRowCount") or 0),
    }


def _registered_vessels(db: Session, unit_id: int) -> list[Vessel]:
    return (
        db.query(Vessel).join(ReportingUnitVessel, ReportingUnitVessel.vessel_id == Vessel.id)
        .filter(ReportingUnitVessel.reporting_unit_id == unit_id).all()
    )


def _candidate_link(vessels: list[Vessel], vessel_name: str) -> tuple[Vessel | None, str, str, str]:
    exact = [item for item in vessels if item.name.strip() == vessel_name.strip()]
    if len(exact) == 1:
        return exact[0], "EXACT", "HIGH", ""
    normalized = normalize_vessel_name(vessel_name)
    candidates = [item for item in vessels if normalize_vessel_name(item.name) == normalized]
    if len(candidates) == 1:
        return candidates[0], "NORMALIZED", "MEDIUM", "REVIEW_NORMALIZED_VESSEL_LINK"
    if not candidates:
        return None, "", "LOW", "UNMATCHED_VESSEL"
    return None, "", "LOW", "AMBIGUOUS_VESSEL"


def _cargo_fact_key(row: dict[str, Any] | HistoricalCargoRow) -> tuple[Any, ...]:
    def value(name: str, default: Any = "") -> Any:
        if isinstance(row, dict):
            return row.get(name, default)
        return getattr(row, name, default)

    numeric_weight = value("weight_tonnes", None)
    return (
        str(value("call_key_normalized")).strip(),
        normalize_token(value("container_size_code_raw")),
        normalize_token(value("full_empty_code_raw")),
        normalize_token(value("trade_scope_raw")),
        normalize_token(value("movement_method_raw")),
        str(value("derived_direction")).strip().lower(),
        str(value("weight_state")).strip().upper(),
        round(float(numeric_weight), 9) if numeric_weight is not None else None,
        normalize_token(value("weight_raw")) if numeric_weight is None else "",
    )


def _pl03_identity(row: dict[str, Any] | HistoricalReportRow) -> str:
    if isinstance(row, HistoricalReportRow):
        if row.normalized_registration:
            return f"r:{row.normalized_registration}"
        dimensions = json.loads(row.mapped_dimensions_json or "{}")
        return f"n:{normalize_vessel_name(dimensions.get('vesselNameRaw'))}"
    registration = normalize_vessel_name(row.get("registration_raw"))
    if registration:
        return f"r:{registration}"
    return f"n:{normalize_vessel_name(row.get('vessel_name_raw'))}"


def _filter_confirmed_sot_rows(
    db: Session,
    *,
    unit_id: int,
    parsed: ParsedWorkbook,
) -> tuple[list[dict[str, Any]], int, list[int]]:
    active_imports = db.query(HistoricalReportImport).filter(
        HistoricalReportImport.reporting_unit_id == unit_id,
        HistoricalReportImport.source_kind == parsed.source_kind,
        HistoricalReportImport.status.in_(ACTIVE_IMPORT_STATUSES),
    )
    if parsed.source_kind == "reported_pl03":
        if not parsed.reporting_period:
            raise ValueError("reported_pl03 requires an explicit reporting period")
        active_imports = active_imports.filter(
            HistoricalReportImport.reporting_period == parsed.reporting_period,
        )
    active_imports = active_imports.all()
    active_ids = [item.id for item in active_imports]
    if not active_ids:
        return list(parsed.rows), 0, []

    retained = 0
    retained_import_ids: set[int] = set()
    new_rows: list[dict[str, Any]] = []
    if parsed.source_kind == "tos_berth_call":
        existing = {
            row.call_key_normalized: row.import_id
            for row in db.query(HistoricalPortCall).filter(
                HistoricalPortCall.reporting_unit_id == unit_id,
                HistoricalPortCall.import_id.in_(active_ids),
                HistoricalPortCall.validation_status != "REJECTED",
            ).all()
            if row.call_key_normalized
        }
        for source in parsed.rows:
            owner = existing.get(source.get("call_key_normalized", ""))
            if owner is None:
                new_rows.append(source)
            else:
                retained += 1
                retained_import_ids.add(owner)
    elif parsed.source_kind == "reported_pl03":
        existing = {
            _pl03_identity(row): row.import_id
            for row in db.query(HistoricalReportRow).filter(
                HistoricalReportRow.reporting_unit_id == unit_id,
                HistoricalReportRow.import_id.in_(active_ids),
                HistoricalReportRow.validation_status != "REJECTED",
            ).all()
            if _pl03_identity(row) not in {"r:", "n:"}
        }
        for source in parsed.rows:
            owner = existing.get(_pl03_identity(source))
            if owner is None:
                new_rows.append(source)
            else:
                retained += 1
                retained_import_ids.add(owner)
    else:
        owners: dict[tuple[Any, ...], list[int]] = {}
        for row in db.query(HistoricalCargoRow).filter(
            HistoricalCargoRow.reporting_unit_id == unit_id,
            HistoricalCargoRow.import_id.in_(active_ids),
            HistoricalCargoRow.validation_status != "REJECTED",
        ).order_by(HistoricalCargoRow.id).all():
            owners.setdefault(_cargo_fact_key(row), []).append(row.import_id)
        remaining = Counter({key: len(import_ids) for key, import_ids in owners.items()})
        used = Counter()
        for source in parsed.rows:
            key = _cargo_fact_key(source)
            if remaining[key] <= 0:
                new_rows.append(source)
                continue
            owner = owners[key][used[key]]
            used[key] += 1
            remaining[key] -= 1
            retained += 1
            retained_import_ids.add(owner)
    return new_rows, retained, sorted(retained_import_ids)


def _active_calls_by_key(
    db: Session, unit_id: int, keys: set[str],
) -> dict[str, list[HistoricalPortCall]]:
    """Load calls in bounded chunks; never perform one lookup per source row."""
    result: dict[str, list[HistoricalPortCall]] = {key: [] for key in keys if key}
    ordered = sorted(result)
    for offset in range(0, len(ordered), 500):
        rows = (
            db.query(HistoricalPortCall)
            .join(HistoricalReportImport, HistoricalReportImport.id == HistoricalPortCall.import_id)
            .filter(
                HistoricalPortCall.reporting_unit_id == unit_id,
                HistoricalPortCall.call_key_normalized.in_(ordered[offset:offset + 500]),
                HistoricalReportImport.reporting_unit_id == unit_id,
                HistoricalReportImport.status.in_(ACTIVE_IMPORT_STATUSES),
            ).all()
        )
        for row in rows:
            result.setdefault(row.call_key_normalized, []).append(row)
    return result


def _stage_berth(db: Session, item: HistoricalReportImport, parsed: ParsedWorkbook) -> None:
    vessels = _registered_vessels(db, item.reporting_unit_id)
    for source in parsed.rows:
        status = source["validation_status"]
        ambiguity = source["ambiguity_status"]
        candidate, method, confidence, link_warning = _candidate_link(
            vessels, source["vessel_name_raw"]
        )
        warnings = list(source["warnings"])
        if link_warning:
            warnings.append(link_warning)
            status = "REVIEW" if status != "REJECTED" else status
            if link_warning == "UNMATCHED_VESSEL":
                ambiguity = "UNMATCHED"
            elif link_warning == "AMBIGUOUS_VESSEL":
                ambiguity = "AMBIGUOUS"
        call = HistoricalPortCall(
            reporting_unit_id=item.reporting_unit_id, import_id=item.id,
            source_sheet=source["source_sheet"], source_row=source["source_row"],
            mapping_version=item.mapping_version,
            vessel_name_raw=source["vessel_name_raw"],
            vessel_name_normalized=source["vessel_name_normalized"],
            call_year_raw=source["call_year_raw"], voyage_number_raw=source["voyage_number_raw"],
            call_key_normalized=source["call_key_normalized"],
            source_berth_raw=source["source_berth_raw"], arrival_berth=source["arrival_berth"],
            departure_berth=source["departure_berth"], berth_correction_json="{}",
            actual_berthing_at_raw=source["actual_berthing_at_raw"],
            actual_berthing_at=source["actual_berthing_at"],
            actual_departure_at_raw=source["actual_departure_at_raw"],
            actual_departure_at=source["actual_departure_at"],
            reporting_month=source["reporting_month"], validation_status=status,
            ambiguity_status=ambiguity, reconciliation_status="NONE",
            provenance_json=json_dumps({**source["provenance"], "warnings": warnings}),
            created_at=now_iso(),
        )
        db.add(call)
        db.flush()
        db.add(HistoricalVesselLink(
            reporting_unit_id=item.reporting_unit_id, import_id=item.id, port_call_id=call.id,
            raw_vessel_name=source["vessel_name_raw"],
            normalized_vessel_name=source["vessel_name_normalized"],
            candidate_vessel_id=candidate.id if candidate else None,
            match_method=method, confidence=confidence, link_status="PENDING",
            reason=link_warning, created_at=now_iso(),
        ))


def _stage_cargo(db: Session, item: HistoricalReportImport, parsed: ParsedWorkbook) -> None:
    periods: set[str] = set()
    calls_by_key = _active_calls_by_key(
        db, item.reporting_unit_id,
        {source["call_key_normalized"] for source in parsed.rows if source["call_key_normalized"]},
    )
    for source in parsed.rows:
        calls = calls_by_key.get(source["call_key_normalized"], [])
        status = source["validation_status"]
        if len(calls) == 1:
            call = calls[0]
            match_status = "MATCHED"
            if call.reporting_month:
                periods.add(call.reporting_month)
        elif not calls:
            call, match_status = None, "UNMATCHED"
            status = "REVIEW" if status != "REJECTED" else status
        else:
            call, match_status = None, "AMBIGUOUS"
            status = "REVIEW" if status != "REJECTED" else status
        db.add(HistoricalCargoRow(
            reporting_unit_id=item.reporting_unit_id, import_id=item.id,
            source_sheet=source["source_sheet"], source_row=source["source_row"],
            port_call_id=call.id if call else None,
            source_call_key_raw=source["source_call_key_raw"],
            call_key_normalized=source["call_key_normalized"],
            container_size_code_raw=source["container_size_code_raw"],
            teu_factor=source["teu_factor"], full_empty_code_raw=source["full_empty_code_raw"],
            trade_scope_raw=source["trade_scope_raw"], movement_method_raw=source["movement_method_raw"],
            derived_direction=source["derived_direction"], weight_raw=source["weight_raw"],
            weight_tonnes=source["weight_tonnes"], weight_state=source["weight_state"],
            transform_version=TRANSFORM_VERSION, match_status=match_status,
            validation_status=status,
            provenance_json=json_dumps({**source["provenance"], "warnings": source["warnings"]}),
            created_at=now_iso(),
        ))
    if len(periods) == 1:
        item.reporting_period = next(iter(periods))


def _stage_pl03(db: Session, item: HistoricalReportImport, parsed: ParsedWorkbook) -> None:
    for source in parsed.rows:
        row = HistoricalReportRow(
            reporting_unit_id=item.reporting_unit_id, import_id=item.id,
            source_sheet=source["source_sheet"], source_row=source["source_row"],
            appendix_row_no=source["appendix_row_no"],
            normalized_registration=normalize_vessel_name(source["registration_raw"]),
            raw_payload_json=json_dumps(source["raw_payload"]),
            mapped_dimensions_json=json_dumps({
                "vesselNameRaw": source["vessel_name_raw"],
                "registrationRaw": source["registration_raw"],
            }), validation_status=source["validation_status"],
            warning_json=json_dumps(source["warnings"]),
            provenance_json=json_dumps(source["provenance"]), created_at=now_iso(),
        )
        db.add(row)
        db.flush()
        for metric in source["metrics"]:
            code = metric["metric_code"]
            db.add(HistoricalReportMetric(
                reporting_unit_id=item.reporting_unit_id, import_id=item.id, row_id=row.id,
                metric_code=code, direction="", category="", unit="tonne" if "tons" in code else "teu",
                value_class="REPORTED_TOTAL", numeric_value=metric["numeric_value"],
                text_value=metric["text_value"], value_state=metric["value_state"],
                source_cell=metric["source_cell"], source_header_raw="",
                mapping_version=item.mapping_version,
                reconciliation_status="REVIEW" if metric["invalid"] else "NONE",
                created_at=now_iso(),
            ))


def _refresh_counts(db: Session, item: HistoricalReportImport) -> None:
    model = {
        "tos_berth_call": HistoricalPortCall,
        "tos_cargo_detail": HistoricalCargoRow,
        "reported_pl03": HistoricalReportRow,
    }[item.source_kind]
    counts = dict(
        db.query(model.validation_status, func.count(model.id))
        .filter(model.import_id == item.id, model.reporting_unit_id == item.reporting_unit_id)
        .group_by(model.validation_status).all()
    )
    item.accepted_count = counts.get("VALID", 0)
    item.review_count = counts.get("REVIEW", 0)
    item.rejected_count = counts.get("REJECTED", 0)
    item.updated_at = now_iso()


def _reconcile_active_cargo_links(db: Session, unit_id: int, actor_user_id: int) -> list[int]:
    """Re-link active cargo after a Berth revision becomes authoritative.

    A corrected Berth file supersedes its former calls.  Cargo facts remain tied
    to their own immutable source import, but their tenant-safe call reference
    must follow the single active call for the audited normalized key.
    """
    cargo_imports = (
        db.query(HistoricalReportImport).filter(
            HistoricalReportImport.reporting_unit_id == unit_id,
            HistoricalReportImport.source_kind == "tos_cargo_detail",
            HistoricalReportImport.status.in_(("PREVIEWED", "COMMITTED", "REVIEW")),
        ).all()
    )
    updated_import_ids: list[int] = []
    for cargo_import in cargo_imports:
        periods: set[str] = set()
        rows = db.query(HistoricalCargoRow).filter_by(
            reporting_unit_id=unit_id, import_id=cargo_import.id,
        ).all()
        before = (
            cargo_import.status, cargo_import.reporting_period,
            cargo_import.accepted_count, cargo_import.review_count,
            tuple((row.id, row.port_call_id, row.match_status, row.validation_status) for row in rows),
        )
        calls_by_key = _active_calls_by_key(
            db, unit_id, {row.call_key_normalized for row in rows if row.call_key_normalized},
        )
        for row in rows:
            calls = calls_by_key.get(row.call_key_normalized, [])
            if len(calls) == 1:
                row.port_call_id = calls[0].id
                row.match_status = "MATCHED"
                if calls[0].reporting_month:
                    periods.add(calls[0].reporting_month)
                if row.validation_status != "REJECTED":
                    warnings = json.loads(row.provenance_json or "{}").get("warnings", [])
                    row.validation_status = "REVIEW" if warnings else "VALID"
            else:
                row.port_call_id = None
                row.match_status = "UNMATCHED" if not calls else "AMBIGUOUS"
                if row.validation_status != "REJECTED":
                    row.validation_status = "REVIEW"
        cargo_import.reporting_period = next(iter(periods)) if len(periods) == 1 else None
        db.flush()
        _refresh_counts(db, cargo_import)
        if cargo_import.status == "REVIEW" and cargo_import.review_count == 0:
            cargo_import.status = "COMMITTED"
        after = (
            cargo_import.status, cargo_import.reporting_period,
            cargo_import.accepted_count, cargo_import.review_count,
            tuple((row.id, row.port_call_id, row.match_status, row.validation_status) for row in rows),
        )
        if before != after:
            updated_import_ids.append(cargo_import.id)
            audit(
                db, "historical_report_import", cargo_import.id, "CARGO_CALLS_RECONCILED",
                f"{cargo_import.accepted_count} valid, {cargo_import.review_count} review",
                actor_user_id=actor_user_id, reporting_unit_id=unit_id,
            )
    return updated_import_ids


def _restage_full_revision(db: Session, item: HistoricalReportImport) -> None:
    receipt = _mapping_receipt(item)
    archive_key = str(receipt.get("sourceArchiveKey") or "")
    archive_root = SOURCE_ARCHIVE_ROOT.resolve()
    source_path = (archive_root / archive_key).resolve()
    if not archive_key or archive_root not in source_path.parents or not source_path.is_file():
        raise HTTPException(
            status_code=409,
            detail="Không thể tạo revision vì file nguồn lưu trữ không còn khả dụng.",
        )
    content = source_path.read_bytes()
    if hashlib.sha256(content).hexdigest() != item.source_checksum:
        raise HTTPException(
            status_code=409,
            detail="Không thể tạo revision vì checksum file nguồn không khớp.",
        )
    try:
        parsed = parse_workbook(content)
    except HistoricalWorkbookError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if parsed.source_kind != item.source_kind:
        raise HTTPException(status_code=409, detail="Loại dữ liệu file nguồn đã thay đổi.")

    if item.source_kind == "tos_berth_call":
        call_ids = [row[0] for row in db.query(HistoricalPortCall.id).filter_by(
            reporting_unit_id=item.reporting_unit_id, import_id=item.id,
        ).all()]
        external_cargo = db.query(HistoricalCargoRow.id).filter(
            HistoricalCargoRow.reporting_unit_id == item.reporting_unit_id,
            HistoricalCargoRow.import_id != item.id,
            HistoricalCargoRow.port_call_id.in_(call_ids or [-1]),
        ).first()
        if external_cargo:
            raise HTTPException(
                status_code=409,
                detail="Không thể restage revision vì lượt preview đã có dữ liệu khác liên kết.",
            )
        db.query(HistoricalVesselLink).filter_by(
            reporting_unit_id=item.reporting_unit_id, import_id=item.id,
        ).delete(synchronize_session=False)
        db.query(HistoricalPortCall).filter_by(
            reporting_unit_id=item.reporting_unit_id, import_id=item.id,
        ).delete(synchronize_session=False)
    elif item.source_kind == "tos_cargo_detail":
        db.query(HistoricalCargoRow).filter_by(
            reporting_unit_id=item.reporting_unit_id, import_id=item.id,
        ).delete(synchronize_session=False)
    else:
        db.query(HistoricalReportMetric).filter_by(
            reporting_unit_id=item.reporting_unit_id, import_id=item.id,
        ).delete(synchronize_session=False)
        db.query(HistoricalReportRow).filter_by(
            reporting_unit_id=item.reporting_unit_id, import_id=item.id,
        ).delete(synchronize_session=False)
    db.flush()

    # PL.03 templates do not carry a trustworthy period in their cells.  Its
    # period is supplied explicitly at preview time and must survive reparsing
    # the archived workbook during a full revision.
    item.reporting_period = parsed.reporting_period or item.reporting_period
    if item.source_kind == "tos_berth_call":
        _stage_berth(db, item, parsed)
    elif item.source_kind == "tos_cargo_detail":
        _stage_cargo(db, item, parsed)
    else:
        _stage_pl03(db, item, parsed)
    db.flush()
    _refresh_counts(db, item)
    receipt.update({
        "activationMode": "FULL_REVISION",
        "newRowCount": len(parsed.rows),
        "sotRetainedCount": 0,
    })
    item.mapping_receipt_json = json_dumps(receipt)


def _conflicts(db: Session, item: HistoricalReportImport) -> list[HistoricalReportImport]:
    query = db.query(HistoricalReportImport).filter(
        HistoricalReportImport.reporting_unit_id == item.reporting_unit_id,
        HistoricalReportImport.source_kind == item.source_kind,
        HistoricalReportImport.id != item.id,
        HistoricalReportImport.status.in_(("COMMITTED", "REVIEW")),
    )
    found: dict[int, HistoricalReportImport] = {}
    sot_import_ids = [
        int(value) for value in _mapping_receipt(item).get("sotImportIds", [])
        if str(value).isdigit()
    ]
    if sot_import_ids:
        for entry in query.filter(HistoricalReportImport.id.in_(sot_import_ids)).all():
            found[entry.id] = entry
    # A parser/mapping correction intentionally creates a new receipt for the
    # same immutable source checksum.  Treat the active older mapping as a
    # conflict even when a legacy report has no reliable reporting period, so
    # confirmation supersedes it instead of leaving two apparently active rows.
    same_source_query = query.filter(
        HistoricalReportImport.source_checksum == item.source_checksum,
    )
    if item.source_kind == "reported_pl03" and item.reporting_period:
        same_source_query = same_source_query.filter(
            HistoricalReportImport.reporting_period == item.reporting_period,
        )
    same_source = same_source_query.all()
    if same_source:
        found.update({entry.id: entry for entry in same_source})
    if item.reporting_period:
        same_period = query.filter(
            HistoricalReportImport.reporting_period == item.reporting_period,
        ).all()
        found.update({entry.id: entry for entry in same_period})
    elif item.source_kind == "tos_cargo_detail":
        ids = [row[0] for row in db.query(HistoricalCargoRow.import_id)
               .filter(HistoricalCargoRow.import_id != item.id,
                       HistoricalCargoRow.reporting_unit_id == item.reporting_unit_id,
                       HistoricalCargoRow.call_key_normalized.in_(
                           db.query(HistoricalCargoRow.call_key_normalized).filter(
                               HistoricalCargoRow.import_id == item.id,
                               HistoricalCargoRow.reporting_unit_id == item.reporting_unit_id,
                            )
                        )).distinct().all()]
        if ids:
            overlap = query.filter(HistoricalReportImport.id.in_(ids)).all()
            found.update({entry.id: entry for entry in overlap})
    return [found[key] for key in sorted(found)]


@router.post("/preview")
async def preview_historical_import(
    request: Request,
    x_source_filename: str | None = Header(default=None, alias="X-Source-Filename"),
    x_reporting_period: str | None = Header(default=None, alias="X-Reporting-Period"),
    db: Session = Depends(get_db), scope: Scope = Depends(require_port_scope),
):
    _authorize(db, scope)
    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="File trống.")
    if len(content) > MAX_SOURCE_BYTES:
        raise HTTPException(status_code=413, detail="File vượt quá giới hạn 12 MB.")
    if not content.startswith(b"PK\x03\x04"):
        raise HTTPException(status_code=400, detail="File không đúng định dạng XLSX.")
    try:
        parsed = parse_workbook(content)
    except HistoricalWorkbookError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if parsed.source_kind == "reported_pl03":
        if not x_reporting_period or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", x_reporting_period):
            raise HTTPException(
                status_code=422,
                detail="Cần chọn kỳ báo cáo hợp lệ (YYYY-MM) cho file PL.03.",
            )
        parsed.reporting_period = x_reporting_period
    checksum = hashlib.sha256(content).hexdigest()
    prior_query = db.query(HistoricalReportImport).filter_by(
        reporting_unit_id=scope.reporting_unit_id, source_kind=parsed.source_kind,
        source_checksum=checksum, mapping_version=parsed.mapping_version,
    )
    if parsed.source_kind == "reported_pl03":
        prior_query = prior_query.filter(
            HistoricalReportImport.reporting_period == parsed.reporting_period,
        )
    prior = prior_query.first()
    if prior:
        _archive_source(scope.reporting_unit_id, checksum, content)
        return {**_import_json(prior, conflicts=[i.id for i in _conflicts(db, prior)]), "idempotent": True}
    archive_key = _archive_source(scope.reporting_unit_id, checksum, content)
    full_row_count = len(parsed.rows)
    new_rows, sot_retained_count, sot_import_ids = _filter_confirmed_sot_rows(
        db, unit_id=scope.reporting_unit_id, parsed=parsed,
    )
    parsed.rows = new_rows
    receipt = dict(parsed.receipt)
    receipt.update({
        "sourceArchiveKey": archive_key,
        "checksumAlgorithm": "sha256",
        "sourceRowCount": full_row_count,
        "sotRetainedCount": sot_retained_count,
        "newRowCount": len(new_rows),
        "sotImportIds": sot_import_ids,
        "activationMode": "INCREMENTAL_PREVIEW",
    })
    item = HistoricalReportImport(
        reporting_unit_id=scope.reporting_unit_id, source_kind=parsed.source_kind,
        appendix_kind=parsed.appendix_kind, mapping_version=parsed.mapping_version,
        reporting_period=parsed.reporting_period, source_filename=_source_filename(x_source_filename),
        source_checksum=checksum, source_size_bytes=len(content),
        source_sheets_json=json_dumps([parsed.sheet_name]), status="PREVIEWED",
        revision_no=1, accepted_count=0, rejected_count=0, review_count=0,
        mapping_receipt_json=json_dumps(receipt), created_by_user_id=scope.user.id,
        created_at=now_iso(), updated_at=now_iso(),
    )
    db.add(item)
    db.flush()
    if parsed.source_kind == "tos_berth_call":
        _stage_berth(db, item, parsed)
    elif parsed.source_kind == "tos_cargo_detail":
        _stage_cargo(db, item, parsed)
    else:
        _stage_pl03(db, item, parsed)
    db.flush()
    _refresh_counts(db, item)
    audit(db, "historical_report_import", item.id, "IMPORT_PREVIEWED",
          f"{item.source_kind} / {item.source_checksum[:12]}", actor_user_id=scope.user.id,
          reporting_unit_id=scope.reporting_unit_id)
    db.commit()
    db.refresh(item)
    return {**_import_json(item, conflicts=[i.id for i in _conflicts(db, item)]), "idempotent": False,
            "mappingReceipt": receipt}


@router.get("")
def list_historical_imports(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db), scope: Scope = Depends(require_port_scope),
):
    _authorize(db, scope)
    query = db.query(HistoricalReportImport).filter_by(reporting_unit_id=scope.reporting_unit_id)
    total = query.count()
    items = query.order_by(HistoricalReportImport.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    current = query.filter(HistoricalReportImport.status.in_(("PREVIEWED", "COMMITTED", "REVIEW")))
    summary = current.with_entities(
        func.coalesce(func.sum(HistoricalReportImport.accepted_count), 0),
        func.coalesce(func.sum(HistoricalReportImport.review_count), 0),
        func.coalesce(func.sum(HistoricalReportImport.rejected_count), 0),
    ).one()
    berth_periods = sorted({period for period, in current.with_entities(
        HistoricalReportImport.reporting_period,
    ).filter(
        HistoricalReportImport.source_kind == "tos_berth_call",
        HistoricalReportImport.reporting_period.isnot(None),
    ).all() if period})
    return {
        "items": [_import_json(item) for item in items],
        "page": page, "pageSize": page_size, "total": total,
        "summary": {
            "accepted": int(summary[0]), "review": int(summary[1]),
            "rejected": int(summary[2]),
        },
        "activeBerthPeriods": berth_periods,
    }


@router.post("/reconcile")
def reconcile_historical_imports(
    db: Session = Depends(get_db), scope: Scope = Depends(require_port_scope),
):
    """Idempotently repair dependent Detail rows from active Berth receipts.

    This endpoint makes recovery independent of browser session and upload order:
    the UI invokes it when the historical workspace opens, while Berth confirm
    still invokes the same reconciliation transaction immediately.
    """
    _authorize(db, scope)
    updated = _reconcile_active_cargo_links(db, scope.reporting_unit_id, scope.user.id)
    db.commit()
    return {"updated": len(updated), "updatedImportIds": updated}


def _historical_pl03_rows(
    db: Session, unit_id: int, reporting_period: str,
) -> tuple[list[list[Any]], dict[str, Any]]:
    active_imports = db.query(HistoricalReportImport).filter(
        HistoricalReportImport.reporting_unit_id == unit_id,
        HistoricalReportImport.status.in_(ACTIVE_IMPORT_STATUSES),
    ).all()
    berth_imports = [
        item for item in active_imports
        if item.source_kind == "tos_berth_call" and item.reporting_period == reporting_period
    ]
    if not berth_imports:
        raise HTTPException(
            status_code=409,
            detail="Chưa có file Berth đã xác nhận cho kỳ này. Mở lượt Berth và xác nhận trước khi xuất PL.03.",
        )
    calls = db.query(HistoricalPortCall).filter(
        HistoricalPortCall.reporting_unit_id == unit_id,
        HistoricalPortCall.import_id.in_([item.id for item in berth_imports]),
        HistoricalPortCall.validation_status != "REJECTED",
    ).order_by(HistoricalPortCall.actual_berthing_at, HistoricalPortCall.id).all()
    if not calls:
        raise HTTPException(status_code=409, detail="File Berth đã xác nhận không có lượt hợp lệ để xuất.")

    cargo_import_ids = [item.id for item in active_imports if item.source_kind == "tos_cargo_detail"]
    cargo_rows = db.query(HistoricalCargoRow).filter(
        HistoricalCargoRow.reporting_unit_id == unit_id,
        HistoricalCargoRow.import_id.in_(cargo_import_ids or [-1]),
        HistoricalCargoRow.port_call_id.in_([call.id for call in calls]),
        HistoricalCargoRow.match_status == "MATCHED",
        HistoricalCargoRow.validation_status == "VALID",
    ).all()
    if not cargo_rows:
        raise HTTPException(
            status_code=409,
            detail="Chưa có chi tiết container đã ghép với Berth cho kỳ này. Hãy đối soát lại các lượt import.",
        )

    # Legacy PL.03 is a dimension scaffold only. Its manual cargo metrics and
    # ETA-era time cells are deliberately ignored in the reconstructed report.
    legacy_imports = sorted(
        [
            item for item in active_imports
            if item.source_kind == "reported_pl03"
            and item.reporting_period == reporting_period
        ],
        key=lambda entry: entry.id,
    )
    legacy_rows = db.query(HistoricalReportRow).filter(
        HistoricalReportRow.reporting_unit_id == unit_id,
        HistoricalReportRow.import_id.in_([item.id for item in legacy_imports] or [-1]),
        HistoricalReportRow.validation_status != "REJECTED",
    ).order_by(
        HistoricalReportRow.import_id,
        HistoricalReportRow.appendix_row_no,
        HistoricalReportRow.id,
    ).all()

    register_ids = [row[0] for row in db.query(ReportingUnitVessel.vessel_id).filter_by(
        reporting_unit_id=unit_id,
    ).all()]
    vessels = db.query(Vessel).filter(Vessel.id.in_(register_ids or [-1])).all()
    vessel_by_id = {vessel.id: vessel for vessel in vessels}
    vessel_by_name = {normalize_vessel_name(vessel.name): vessel for vessel in vessels}
    vessel_by_registration = {
        normalize_vessel_name(vessel.registration_no): vessel for vessel in vessels
        if vessel.registration_no
    }

    def legacy_payload(row: HistoricalReportRow) -> dict[str, Any]:
        return json.loads(row.raw_payload_json or "{}")

    def group_key(name: str, registration: str = "", vessel_id: int | None = None) -> str:
        if vessel_id:
            return f"v:{vessel_id}"
        vessel = vessel_by_registration.get(normalize_vessel_name(registration))
        vessel = vessel or vessel_by_name.get(normalize_vessel_name(name))
        return f"v:{vessel.id}" if vessel else f"n:{normalize_vessel_name(name)}"

    groups: OrderedDict[str, dict[str, Any]] = OrderedDict()
    legacy_identity_keys: dict[str, str | None] = {}
    for legacy in legacy_rows:
        raw = legacy_payload(legacy)
        name = str(raw.get("B") or "").strip()
        registration = str(raw.get("C") or "").strip()
        key = group_key(name, registration)
        groups.setdefault(key, {"legacy": legacy, "calls": [], "cargo": []})
        for identity in (normalize_vessel_name(name), normalize_vessel_name(registration)):
            if not identity:
                continue
            if identity not in legacy_identity_keys:
                legacy_identity_keys[identity] = key
            elif legacy_identity_keys[identity] != key:
                legacy_identity_keys[identity] = None

    def call_group_key(call: HistoricalPortCall) -> str:
        if call.vessel_id:
            return f"v:{call.vessel_id}"
        legacy_key = legacy_identity_keys.get(normalize_vessel_name(call.vessel_name_raw))
        return legacy_key or group_key(call.vessel_name_raw)

    for call in calls:
        key = call_group_key(call)
        groups.setdefault(key, {"legacy": None, "calls": [], "cargo": []})["calls"].append(call)
    call_group = {call.id: call_group_key(call) for call in calls}
    for cargo in cargo_rows:
        key = call_group.get(cargo.port_call_id)
        if key:
            groups.setdefault(key, {"legacy": None, "calls": [], "cargo": []})["cargo"].append(cargo)

    def distinct(values: list[Any]) -> str:
        result: list[str] = []
        for value in values:
            text = str(value or "").strip()
            if text and text not in result:
                result.append(text)
        return "\n".join(result)

    rows: list[list[Any]] = []
    for key, group in groups.items():
        calls_for_vessel: list[HistoricalPortCall] = group["calls"]
        legacy = group["legacy"]
        raw = legacy_payload(legacy) if legacy else {}
        linked_id = next((call.vessel_id for call in calls_for_vessel if call.vessel_id), None)
        if linked_id is None and key.startswith("v:"):
            linked_id = int(key.split(":", 1)[1])
        vessel = vessel_by_id.get(linked_id)
        fallback_name = calls_for_vessel[0].vessel_name_raw if calls_for_vessel else raw.get("B", "")
        row: list[Any] = [None] * 35
        row[0] = len(rows) + 1
        row[1] = (vessel.name if vessel else None) or raw.get("B") or fallback_name
        row[2] = (vessel.registration_no if vessel else None) or raw.get("C") or ""
        row[3] = (vessel.vessel_type if vessel else None) or raw.get("D") or ""
        row[4] = (vessel.vessel_class if vessel else None) or raw.get("E") or ""
        row[5] = (vessel.length_m if vessel else None) or raw.get("F")
        row[6] = (vessel.deadweight_tons if vessel else None) or raw.get("G")
        row[7] = (vessel.gross_tonnage if vessel else None) or raw.get("H")
        for cargo in group["cargo"]:
            if normalize_token(cargo.trade_scope_raw) == "HANG NOI":
                start = 14 if cargo.derived_direction == "unload" else 17
            else:
                start = 11 if cargo.derived_direction == "unload" else 8
            row[start] = float(row[start] or 0) + float(cargo.weight_tonnes or 0)
            teu_column = start + 2 if cargo.full_empty_code_raw == "E" else start + 1
            row[teu_column] = float(row[teu_column] or 0) + float(cargo.teu_factor or 0)
        for index in range(8, 28):
            if isinstance(row[index], float):
                row[index] = round(row[index], 6)
        row[28] = "Container" if group["cargo"] else ""
        row[29] = raw.get("AD") or ""
        row[30] = raw.get("AE") or ""
        row[31] = raw.get("AF") or ""
        row[32] = distinct([call.actual_berthing_at_raw for call in calls_for_vessel])
        row[33] = distinct([call.actual_departure_at_raw for call in calls_for_vessel])
        row[34] = raw.get("AI") or ""
        rows.append(row)
    return rows, {
        "berthImportIds": [item.id for item in berth_imports],
        "cargoImportIds": sorted({row.import_id for row in cargo_rows}),
        "legacyPl03ImportId": legacy_imports[-1].id if legacy_imports else None,
        "legacyPl03ImportIds": [item.id for item in legacy_imports],
        "callCount": len(calls), "cargoRowCount": len(cargo_rows), "reportRowCount": len(rows),
    }


@router.get("/exports/pl03")
def export_historical_pl03(
    reporting_period: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    db: Session = Depends(get_db), scope: Scope = Depends(require_port_scope),
):
    _authorize(db, scope)
    _reconcile_active_cargo_links(db, scope.reporting_unit_id, scope.user.id)
    db.commit()
    rows, receipt = _historical_pl03_rows(db, scope.reporting_unit_id, reporting_period)
    unit = db.get(ReportingUnit, scope.reporting_unit_id)
    year, month = map(int, reporting_period.split("-"))
    content = make_report_xlsx(
        "appendix3", rows,
        appendix3_template=ROOT / "templates" / "Phụ lục 3.xlsx",
        report_from=date(year, month, 1), report_to=date(year, month, 1),
        reporting_unit=unit.name if unit else "",
    )
    receipt_header = json.dumps(receipt, separators=(",", ":"))
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="PL03_TOS_{reporting_period}.xlsx"',
            "X-Historical-Receipt": receipt_header,
        },
    )


@router.get("/{import_id}")
def historical_import_detail(
    import_id: int, db: Session = Depends(get_db), scope: Scope = Depends(require_port_scope),
):
    _authorize(db, scope)
    item = db.query(HistoricalReportImport).filter_by(
        id=import_id, reporting_unit_id=scope.reporting_unit_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy lượt import.")
    return {
        **_import_json(item, conflicts=[entry.id for entry in _conflicts(db, item)]),
        "mappingReceipt": json.loads(item.mapping_receipt_json or "{}"),
        "sourceSheets": json.loads(item.source_sheets_json or "[]"),
        "supersedeReason": item.supersede_reason,
    }


@router.get("/{import_id}/rows")
def historical_import_rows(
    import_id: int, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    status_filter: Literal["VALID", "REVIEW", "REJECTED"] | None = Query(
        default=None, alias="status"
    ),
    db: Session = Depends(get_db), scope: Scope = Depends(require_port_scope),
):
    _authorize(db, scope)
    item = db.query(HistoricalReportImport).filter_by(id=import_id, reporting_unit_id=scope.reporting_unit_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy lượt import.")
    model = {"tos_berth_call": HistoricalPortCall, "tos_cargo_detail": HistoricalCargoRow,
             "reported_pl03": HistoricalReportRow}[item.source_kind]
    query = db.query(model).filter_by(import_id=item.id, reporting_unit_id=scope.reporting_unit_id)
    if status_filter:
        query = query.filter(model.validation_status == status_filter)
    total = query.count()
    rows = query.order_by(model.source_row).offset((page - 1) * page_size).limit(page_size).all()
    if model is HistoricalPortCall:
        payload = [{"id": row.id, "sourceRow": row.source_row, "vesselName": row.vessel_name_raw,
                    "year": row.call_year_raw, "voyage": row.voyage_number_raw,
                    "berth": row.source_berth_raw, "atb": row.actual_berthing_at_raw,
                    "atd": row.actual_departure_at_raw, "reportingMonth": row.reporting_month,
                    "validationStatus": row.validation_status, "ambiguityStatus": row.ambiguity_status,
                    "warnings": json.loads(row.provenance_json or "{}").get("warnings", []),
                    "provenance": json.loads(row.provenance_json)} for row in rows]
    elif model is HistoricalCargoRow:
        payload = [{"id": row.id, "sourceRow": row.source_row, "sourceCallKey": row.source_call_key_raw,
                    "size": row.container_size_code_raw, "teuFactor": row.teu_factor,
                    "fullEmpty": row.full_empty_code_raw, "trade": row.trade_scope_raw,
                    "method": row.movement_method_raw, "direction": row.derived_direction,
                    "weightTonnes": row.weight_tonnes, "weightState": row.weight_state,
                    "matchStatus": row.match_status, "validationStatus": row.validation_status,
                    "warnings": json.loads(row.provenance_json or "{}").get("warnings", []),
                    "provenance": json.loads(row.provenance_json)} for row in rows]
    else:
        payload = [{"id": row.id, "sourceRow": row.source_row, "appendixRowNo": row.appendix_row_no,
                    "dimensions": json.loads(row.mapped_dimensions_json),
                    "validationStatus": row.validation_status, "warnings": json.loads(row.warning_json),
                    "provenance": json.loads(row.provenance_json)} for row in rows]
    return {"items": payload, "page": page, "pageSize": page_size, "total": total,
            "status": status_filter}


@router.get("/{import_id}/vessel-links")
def historical_vessel_links(
    import_id: int, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    status_filter: Literal["PENDING", "ACCEPTED", "REJECTED"] | None = Query(
        default=None, alias="status"
    ),
    db: Session = Depends(get_db), scope: Scope = Depends(require_port_scope),
):
    _authorize(db, scope)
    item = db.query(HistoricalReportImport).filter_by(
        id=import_id, reporting_unit_id=scope.reporting_unit_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy lượt import.")
    query = db.query(HistoricalVesselLink).filter_by(
        import_id=import_id, reporting_unit_id=scope.reporting_unit_id,
    )
    if status_filter:
        query = query.filter(HistoricalVesselLink.link_status == status_filter)
    total = query.count()
    links = query.order_by(HistoricalVesselLink.id).offset((page - 1) * page_size).limit(page_size).all()
    candidates = {
        vessel.id: vessel for vessel in db.query(Vessel).filter(
            Vessel.id.in_([link.candidate_vessel_id for link in links if link.candidate_vessel_id])
        ).all()
    }
    return {
        "items": [{
            "id": link.id, "portCallId": link.port_call_id,
            "rawVesselName": link.raw_vessel_name,
            "normalizedVesselName": link.normalized_vessel_name,
            "rawRegistration": link.raw_registration,
            "candidateVesselId": link.candidate_vessel_id,
            "candidateVesselName": candidates.get(link.candidate_vessel_id).name
                if candidates.get(link.candidate_vessel_id) else None,
            "candidateRegistration": candidates.get(link.candidate_vessel_id).registration_no
                if candidates.get(link.candidate_vessel_id) else None,
            "matchMethod": link.match_method, "confidence": link.confidence,
            "status": link.link_status, "reason": link.reason,
        } for link in links],
        "page": page, "pageSize": page_size, "total": total,
    }


@router.post("/{import_id}/cancel")
def cancel_historical_import(
    import_id: int, body: CancelHistoricalImport,
    db: Session = Depends(get_db), scope: Scope = Depends(require_port_scope),
):
    _authorize(db, scope)
    item = db.query(HistoricalReportImport).filter_by(
        id=import_id, reporting_unit_id=scope.reporting_unit_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy lượt import.")
    if item.status == "REJECTED":
        return {**_import_json(item), "idempotent": True}
    if item.status != "PREVIEWED":
        raise HTTPException(status_code=409, detail="Chỉ có thể hủy lượt import đang ở bước preview.")
    item.status = "REJECTED"
    item.supersede_reason = body.reason.strip() or "Người dùng hủy sau khi xem preview."
    item.updated_at = now_iso()
    audit(db, "historical_report_import", item.id, "IMPORT_PREVIEW_CANCELLED",
          item.supersede_reason, actor_user_id=scope.user.id,
          reporting_unit_id=scope.reporting_unit_id)
    db.commit()
    return _import_json(item)


@router.post("/{import_id}/confirm")
def confirm_historical_import(
    import_id: int, body: ConfirmHistoricalImport,
    db: Session = Depends(get_db), scope: Scope = Depends(require_port_scope),
):
    _authorize(db, scope)
    item = db.query(HistoricalReportImport).filter_by(id=import_id, reporting_unit_id=scope.reporting_unit_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy lượt import.")
    if item.status != "PREVIEWED":
        return {**_import_json(item), "idempotent": True}
    conflicts = _conflicts(db, item)
    if body.supersedes_import_id is not None:
        if body.supersedes_import_id not in {entry.id for entry in conflicts}:
            raise HTTPException(status_code=409, detail="Bản được chọn không phải xung đột cùng đơn vị/nguồn/kỳ.")
    if conflicts and body.conflict_action is None:
        raise HTTPException(status_code=409, detail={
            "message": "Dữ liệu trùng phạm vi đã lưu; cần chọn giữ SOT, bổ sung phát sinh mới hoặc kích hoạt revision mới.",
            "conflictingImportIds": [entry.id for entry in conflicts],
        })
    if conflicts and body.conflict_action == "KEEP_EXISTING":
        item.status = "REJECTED"
        item.supersede_reason = body.reason or "Giữ dữ liệu hiện có theo xác nhận người dùng."
        item.updated_at = now_iso()
        audit(db, "historical_report_import", item.id, "IMPORT_CONFLICT_KEEP_EXISTING",
              item.supersede_reason, actor_user_id=scope.user.id, reporting_unit_id=scope.reporting_unit_id)
        db.commit()
        return _import_json(item, conflicts=[entry.id for entry in conflicts])
    if conflicts and body.conflict_action == "MERGE_NEW_RECORDS":
        receipt = _mapping_receipt(item)
        if int(receipt.get("newRowCount") or 0) <= 0:
            raise HTTPException(
                status_code=409,
                detail="File không có phát sinh mới; hãy chọn giữ dữ liệu SOT hiện có.",
            )
        item.status = "REVIEW" if item.review_count else "COMMITTED"
        item.supersede_reason = body.reason.strip() or "Bổ sung phát sinh mới; giữ nguyên SOT đã xác nhận."
        item.updated_at = now_iso()
        receipt["activationMode"] = "INCREMENTAL_MERGE"
        item.mapping_receipt_json = json_dumps(receipt)
        audit(
            db, "historical_report_import", item.id, "IMPORT_INCREMENTAL_MERGE",
            f"{receipt.get('sotRetainedCount', 0)} SOT retained; "
            f"{receipt.get('newRowCount', 0)} new rows",
            actor_user_id=scope.user.id, reporting_unit_id=scope.reporting_unit_id,
        )
    elif conflicts:
        if not body.reason.strip():
            raise HTTPException(status_code=422, detail="Cần ghi lý do khi kích hoạt revision mới.")
        _restage_full_revision(db, item)
        item.revision_no = max(entry.revision_no for entry in conflicts) + 1
        for prior in conflicts:
            prior.status = "SUPERSEDED"
            prior.superseded_by_import_id = item.id
            prior.supersede_reason = body.reason.strip()
            prior.updated_at = now_iso()
        item.status = "REVIEW" if item.review_count else "COMMITTED"
        item.supersede_reason = body.reason.strip()
    else:
        item.status = "REVIEW" if item.review_count else "COMMITTED"
        item.supersede_reason = body.reason.strip()
    item.updated_at = now_iso()
    audit(db, "historical_report_import", item.id, "IMPORT_CONFIRMED",
          f"{item.source_kind} revision {item.revision_no}; {item.accepted_count} valid, "
          f"{item.review_count} review, {item.rejected_count} rejected",
          actor_user_id=scope.user.id, reporting_unit_id=scope.reporting_unit_id)
    db.flush()
    if item.source_kind == "tos_berth_call":
        _reconcile_active_cargo_links(db, scope.reporting_unit_id, scope.user.id)
    db.commit()
    db.refresh(item)
    return _import_json(item, conflicts=[entry.id for entry in conflicts])


@router.post("/{import_id}/vessel-links/{link_id}/resolve")
def resolve_historical_vessel_link(
    import_id: int, link_id: int, body: ResolveVesselLink,
    db: Session = Depends(get_db), scope: Scope = Depends(require_port_scope),
):
    _authorize(db, scope, reviewer=True)
    link = db.query(HistoricalVesselLink).filter_by(
        id=link_id, import_id=import_id, reporting_unit_id=scope.reporting_unit_id,
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Không tìm thấy liên kết phương tiện.")
    item = db.query(HistoricalReportImport).filter_by(
        id=import_id, reporting_unit_id=scope.reporting_unit_id,
    ).one()
    if item.status in {"REJECTED", "SUPERSEDED"}:
        raise HTTPException(
            status_code=409,
            detail="Không thể xử lý liên kết của lượt import đã hủy hoặc đã được thay thế.",
        )
    if body.decision == "ACCEPT":
        candidate_id = body.candidate_vessel_id or link.candidate_vessel_id
        if candidate_id is None:
            raise HTTPException(status_code=422, detail="Cần chọn phương tiện để chấp nhận liên kết.")
        try:
            validate_vessel_link_tenant(
                db, reporting_unit_id=scope.reporting_unit_id, candidate_vessel_id=candidate_id,
            )
        except HistoricalTenantError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        previous_candidate_id = link.candidate_vessel_id
        link.candidate_vessel_id = candidate_id
        link.link_status = "ACCEPTED"
        link.match_method = "MANUAL" if candidate_id != previous_candidate_id else link.match_method
        if link.port_call_id:
            call = db.query(HistoricalPortCall).filter_by(
                id=link.port_call_id, reporting_unit_id=scope.reporting_unit_id,
            ).first()
            if call:
                call.vessel_id = candidate_id
                if call.ambiguity_status in {"UNMATCHED", "AMBIGUOUS"}:
                    call.ambiguity_status = "NONE"
                original_warnings = json.loads(call.provenance_json or "{}").get("warnings", [])
                link_warnings = {
                    "REVIEW_NORMALIZED_VESSEL_LINK", "UNMATCHED_VESSEL", "AMBIGUOUS_VESSEL",
                }
                if call.validation_status != "REJECTED" and not any(
                    warning not in link_warnings for warning in original_warnings
                ):
                    call.validation_status = "VALID"
    else:
        link.link_status = "REJECTED"
    link.reason = body.reason.strip()
    link.reviewed_by_user_id = scope.user.id
    link.reviewed_at = now_iso()
    audit(db, "historical_vessel_link", link.id, f"LINK_{link.link_status}",
          link.reason or link.raw_vessel_name, actor_user_id=scope.user.id,
          reporting_unit_id=scope.reporting_unit_id)
    db.flush()
    _refresh_counts(db, item)
    if item.status == "REVIEW" and item.review_count == 0:
        item.status = "COMMITTED"
    db.commit()
    return {"id": link.id, "status": link.link_status, "candidateVesselId": link.candidate_vessel_id}
