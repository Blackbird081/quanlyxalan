"""Import dữ liệu vận hành từ Excel: sổ theo dõi, phương tiện, thuyền viên, phiếu.

Tách khỏi backend/app.py (khối "IMPORT (Excel)") — chỉ di chuyển, không đổi
logic. Router giữ nguyên đường dẫn cũ nên hợp đồng API không đổi.

Khác với import lịch sử/TOS (backend/historical_api.py) vốn ghi vào kho dữ
liệu đối soát riêng: các route ở đây ghi thẳng vào dữ liệu vận hành LIVE.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .database import audit, cargo, get_db, now_iso
from .models import (
    CrewMember, Declaration, ImportJob, Organization, ReportingUnitOrganization,
    ReportingUnitVessel, Vessel,
)
from .shared import (
    CREW_ROLE_CANONICAL, IMPORT_MAPPING_VERSION, _get_or_create_org,
    _resolve_org_for_port_scope, _sync_vessel_operating_profiles,
    access_logger, remove_demo_data_for_real_input, validate_attachment_content,
)
from .tenant import (
    Scope, require_port_scope, require_vessel_in_scope, resolve_scope,
    scope_allows_vessel,
)
from .xlsx_io import (
    crew_rows, declaration_row, excel_date, import_match_key, read_workbook,
    vessel_rows,
)


router = APIRouter(tags=["import"])
VESSEL_IMPORT_COMPARE_FIELDS = {
    "name": "Tên phương tiện",
    "vessel_type": "Loại phương tiện",
    "vessel_class": "Cấp phương tiện",
    "registry_or_imo": "Số đăng kiểm / IMO",
    "shell_material": "Vật liệu vỏ",
    "build_year": "Năm đóng",
    "length_m": "Chiều dài",
    "width_m": "Chiều rộng",
    "side_height_m": "Chiều cao mạn",
    "draft_m": "Mớn nước",
    "deadweight_tons": "Trọng tải",
    "gross_tonnage": "Dung tích",
    "engine_power_cv": "Công suất",
    "cargo_capacity_tons": "Sức chở hàng",
    "container_capacity_teu": "Sức chở container",
    "passenger_capacity": "Sức chở khách",
    "min_crew": "Số thuyền viên",
    "safety_certificate_no": "Số chứng nhận an toàn",
    "certificate_issue_date": "Ngày cấp chứng nhận",
    "certificate_expiry_date": "Ngày hết hạn chứng nhận",
    "tracking_master_name": "Thuyền trưởng theo dõi",
    "tracking_master_phone": "Số điện thoại liên hệ",
    "notes": "Ghi chú",
}


def _vessel_import_changes(existing: Vessel, row: dict[str, Any]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for field, label in VESSEL_IMPORT_COMPARE_FIELDS.items():
        if field not in row:
            continue
        incoming = excel_date(row[field]) if "date" in field else row[field]
        current = getattr(existing, field, None)
        if current != incoming:
            changes.append({
                "field": field,
                "label": label,
                "current": current,
                "incoming": incoming,
            })
    incoming_profiles = [
        (
            profile.get("activity_area") or "",
            profile.get("deadweight_tons"),
            profile.get("cargo_capacity_tons"),
        )
        for profile in row.get("operating_profiles", [])
    ]
    current_profiles = [
        (profile.activity_area, profile.deadweight_tons, profile.cargo_capacity_tons)
        for profile in existing.operating_profiles
    ]
    if incoming_profiles and incoming_profiles != current_profiles:
        changes.append({
            "field": "operating_profiles",
            "label": "Vùng hoạt động / trọng tải / khả năng khai thác",
            "current": current_profiles,
            "incoming": incoming_profiles,
        })
    return changes

@router.post("/api/import/port-vessel-register")
@router.post("/api/import/vessels")
async def import_vessels(
    request: Request,
    preview: bool = False,
    overwrite_existing: bool = False,
    db: Session = Depends(get_db),
    scope: Scope = Depends(resolve_scope),
):
    user = scope.user
    is_port_register = request.url.path.endswith("/port-vessel-register")
    if is_port_register and scope.is_customer:
        raise HTTPException(status_code=403, detail="Sổ theo dõi Salan chỉ dành cho Nhân viên Cảng và Admin.")
    import_kind = "PORT_VESSEL_REGISTER" if is_port_register else "VESSELS"
    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="File trống.")
    validate_attachment_content(".xlsx", content)
    try:
        sheets = read_workbook(content)
        org_data, rows = vessel_rows(sheets)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Lỗi đọc file: {exc}")

    # Scoping organization based on scope
    if scope.is_customer:
        org_id = user.organization_id
    elif is_port_register:
        # Register membership is vessel-scoped, but its customer-owned master
        # remains constrained to an Organization linked to this unit.
        org = _resolve_org_for_port_scope(db, scope, org_data.get("name"))
        org_id = org.id if org else None
    else:
        org = _resolve_org_for_port_scope(db, scope, org_data.get("name"))
        org_id = org.id if org else None

    checksum = hashlib.sha256(content).hexdigest()
    required_vessel_fields = {
        "name": "Tên phương tiện",
        "registration_no": "Số đăng ký",
        "vessel_type": "Loại phương tiện",
        "vessel_class": "Cấp phương tiện",
    }
    preview_rows = []
    conflict_count = 0
    for row in rows:
        clean_row = {key: value for key, value in row.items() if not key.startswith("_")}
        clean_row["sourceRow"] = row.get("_source_row")
        clean_row["sourceSheet"] = row.get("_source_sheet")
        clean_row["mappingWarnings"] = row.get("_mapping_warnings", [])
        clean_row["missingFields"] = [
            label for field, label in required_vessel_fields.items() if not row.get(field)
        ]
        existing = db.query(Vessel).filter(
            Vessel.registration_no == row.get("registration_no")
        ).first() if row.get("registration_no") else None
        if existing:
            conflict_count += 1
            same_scope = scope_allows_vessel(db, scope, existing)
            clean_row["existing"] = True
            clean_row["ownershipConflict"] = bool(overwrite_existing and not same_scope)
            if same_scope:
                clean_row["existingRecord"] = {
                    "id": existing.id,
                    "name": existing.name,
                    "registration_no": existing.registration_no,
                }
                clean_row["changes"] = _vessel_import_changes(existing, row)
        else:
            clean_row["existing"] = False
            clean_row["ownershipConflict"] = False
            clean_row["changes"] = []
        preview_rows.append(clean_row)
    prior = db.query(ImportJob).filter(
        ImportJob.organization_id == org_id,
        ImportJob.reporting_unit_id == (scope.reporting_unit_id if scope.is_port else None),
        ImportJob.import_kind == import_kind,
        ImportJob.source_checksum == checksum,
        ImportJob.mapping_version == IMPORT_MAPPING_VERSION,
    ).first()
    if preview:
        db.rollback()
        return {
            "preview": True,
            "mappingVersion": IMPORT_MAPPING_VERSION,
            "checksum": checksum,
            "organization": org_data,
            "mapping": {
                "strategy": "HEADER_LABEL_DETECTION",
                "sheet": rows[0].get("_source_sheet") if rows else None,
            },
            "rows": preview_rows,
            "conflictCount": conflict_count,
            "previousImportId": prior.id if prior else None,
            "accepted": 0,
            "rejected": [],
        }
    if prior and not overwrite_existing:
        result = json.loads(prior.result_json)
        result["idempotent"] = True
        result["importJobId"] = prior.id
        return result

    remove_demo_data_for_real_input(
        db,
        retain_organization_id=org_id if scope.is_customer else None,
        organization_data=org_data,
        allowed_organization_ids=scope.member_org_ids if scope.is_port else None,
    )

    accepted = 0
    created = 0
    updated = 0
    skipped = 0
    rejected: list[dict] = []
    for row in rows:
        source_row = row.get("_source_row")
        missing_fields = [
            label for field, label in required_vessel_fields.items() if not row.get(field)
        ]
        if missing_fields:
            rejected.append({
                "sourceRow": source_row,
                "row": row.get("name"),
                "error": f"Thiếu {', '.join(missing_fields)}",
            })
            continue
        try:
            with db.begin_nested():
                existing = db.query(Vessel).filter(
                    Vessel.registration_no == row.get("registration_no")
                ).first()
                if existing:
                    if not overwrite_existing:
                        skipped += 1
                        if not is_port_register:
                            continue
                        # A port may link an existing shared Vessel master into
                        # its own register without mutating that master.
                        vessel = existing
                    else:
                        # Adding a register link may span master ownership, but an
                        # overwrite is still a tenant-bound master-data mutation.
                        require_vessel_in_scope(db, scope, existing)
                        for k, v in row.items():
                            if k != "operating_profiles" and hasattr(existing, k) and k not in ("id", "created_at", "organization_id"):
                                setattr(existing, k, excel_date(v) if "date" in k else v)
                        _sync_vessel_operating_profiles(existing, row.get("operating_profiles", []))
                        existing.organization_id = org_id
                        existing.updated_at = now_iso()
                        if is_port_register:
                            existing.is_port_tracked = 1
                            existing.port_tracking_updated_at = existing.updated_at
                        existing.version += 1
                        updated += 1
                        vessel = existing
                else:
                    safe = {
                        k: (excel_date(v) if "date" in k else v)
                        for k, v in row.items()
                        if not k.startswith("_") and hasattr(Vessel, k) and k not in ("id", "organization_id", "operating_profiles")
                    }
                    safe["organization_id"] = org_id
                    safe["created_at"] = now_iso()
                    safe["updated_at"] = now_iso()
                    if is_port_register:
                        safe["is_port_tracked"] = 1
                        safe["port_tracking_updated_at"] = safe["updated_at"]
                    vessel = Vessel(**safe)
                    db.add(vessel)
                    db.flush()
                    _sync_vessel_operating_profiles(vessel, row.get("operating_profiles", []))
                    created += 1
                if is_port_register and scope.is_port:
                    link = (
                        db.query(ReportingUnitVessel)
                        .filter_by(reporting_unit_id=scope.reporting_unit_id, vessel_id=vessel.id)
                        .first()
                    )
                    if link is None:
                        db.add(ReportingUnitVessel(
                            reporting_unit_id=scope.reporting_unit_id, vessel_id=vessel.id,
                            added_by_user_id=user.id, created_at=now_iso(),
                        ))
                db.flush()
            accepted += 1
        except Exception:
            access_logger.exception(
                "Vessel import row rejected source_row=%s registration_no=%s",
                source_row, row.get("registration_no"),
            )
            rejected.append({
                "sourceRow": source_row,
                "row": row.get("name"),
                "error": "Không thể nhập dòng này. Hãy kiểm tra định dạng số, ngày hoặc mã đăng ký trùng.",
            })
    result = {
        "accepted": accepted,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "rejected": rejected,
        "mappingVersion": IMPORT_MAPPING_VERSION,
        "checksum": checksum,
        "idempotent": False,
    }
    if prior:
        result["reapplied"] = True
        result["importJobId"] = prior.id
        prior.accepted_count = accepted
        prior.rejected_count = len(rejected)
        prior.result_json = json.dumps(result, ensure_ascii=False)
        db.commit()
        return result
    job = ImportJob(
        organization_id=org_id, import_kind=import_kind, source_checksum=checksum,
        reporting_unit_id=scope.reporting_unit_id if scope.is_port else None,
        mapping_version=IMPORT_MAPPING_VERSION, accepted_count=accepted,
        rejected_count=len(rejected), result_json=json.dumps(result, ensure_ascii=False),
        created_by_user_id=user.id, created_at=now_iso(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    result["importJobId"] = job.id
    return result


CREW_IMPORT_COMPARE_FIELDS = {
    "full_name": "Họ và tên",
    "crew_role": "Chức danh",
    "birth_date": "Ngày sinh",
    "phone": "Số điện thoại",
    "identity_no": "CCCD / Hộ chiếu",
    "professional_certificate_type": "Loại chứng chỉ",
    "professional_certificate_no": "Số chứng chỉ",
    "certificate_issue_date": "Ngày cấp",
    "certificate_expiry_date": "Ngày hết hạn",
    "notes": "Ghi chú",
}


def _import_organization(db: Session, name: str) -> Organization | None:
    key = import_match_key(name)
    return next(
        (organization for organization in db.query(Organization).all()
         if import_match_key(organization.name) == key),
        None,
    )


def _existing_import_crew(
    db: Session, organization_id: int, row: dict[str, Any],
) -> CrewMember | None:
    query = db.query(CrewMember).filter(CrewMember.organization_id == organization_id)
    identity_no = str(row.get("identity_no") or "").strip()
    certificate_no = str(row.get("professional_certificate_no") or "").strip()
    if identity_no:
        existing = query.filter(CrewMember.identity_no == identity_no).first()
        if existing:
            return existing
    if certificate_no:
        return query.filter(CrewMember.professional_certificate_no == certificate_no).first()
    birth_date = row.get("birth_date")
    if birth_date:
        return query.filter(
            CrewMember.full_name == row.get("full_name"),
            CrewMember.birth_date == birth_date,
        ).first()
    return None


def _crew_import_changes(existing: CrewMember, row: dict[str, Any]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for field, label in CREW_IMPORT_COMPARE_FIELDS.items():
        if field not in row:
            continue
        current = getattr(existing, field, None)
        incoming = row[field]
        if current != incoming:
            changes.append({
                "field": field,
                "label": label,
                "current": current,
                "incoming": incoming,
            })
    return changes


@router.post("/api/import/crew")
async def import_crew(
    request: Request,
    preview: bool = False,
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    user = scope.user
    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="File trống.")
    validate_attachment_content(".xlsx", content)
    try:
        rows = crew_rows(read_workbook(content))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Lỗi đọc file: {exc}")

    checksum = hashlib.sha256(content).hexdigest()
    required_fields = {
        "organization_name": "Tên doanh nghiệp",
        "full_name": "Họ và tên",
        "crew_role": "Chức danh",
    }
    prepared: list[tuple[dict[str, Any], Organization | None, CrewMember | None]] = []
    preview_rows: list[dict[str, Any]] = []
    for row in rows:
        raw_role = str(row.get("crew_role") or "")
        canonical_role = CREW_ROLE_CANONICAL.get(import_match_key(raw_role))
        if canonical_role:
            row["crew_role"] = canonical_role
        elif raw_role:
            row["_invalid_crew_role"] = raw_role
        organization = _import_organization(db, str(row.get("organization_name") or ""))
        existing = _existing_import_crew(db, organization.id, row) if organization else None
        missing = [label for field, label in required_fields.items() if not row.get(field)]
        if row.get("_invalid_crew_role"):
            missing.append("Chức danh hợp lệ")
        if row.get("organization_name") and not organization:
            missing.append("Doanh nghiệp đã có trong hệ thống")
        clean = {key: value for key, value in row.items() if not key.startswith("_")}
        clean.update({
            "sourceRow": row.get("_source_row"),
            "sourceSheet": row.get("_source_sheet"),
            "mappingWarnings": row.get("_mapping_warnings", []),
            "missingFields": missing,
            "existing": bool(existing),
            "changes": _crew_import_changes(existing, row) if existing else [],
        })
        preview_rows.append(clean)
        prepared.append((row, organization, existing))

    recognized_organization_ids = {
        organization.id for _, organization, _ in prepared if organization
    }
    if len(recognized_organization_ids) > 1:
        raise HTTPException(
            status_code=422,
            detail="Mỗi file thuyền viên chỉ được chứa dữ liệu của một doanh nghiệp.",
        )
    job_organization_id = next(iter(recognized_organization_ids), None)
    if job_organization_id is not None:
        scope.require_org(job_organization_id)
    prior = db.query(ImportJob).filter(
        ImportJob.organization_id == job_organization_id,
        ImportJob.reporting_unit_id == scope.reporting_unit_id,
        ImportJob.import_kind == "CREW",
        ImportJob.source_checksum == checksum,
        ImportJob.mapping_version == IMPORT_MAPPING_VERSION,
    ).first()
    if preview:
        return {
            "preview": True,
            "mappingVersion": IMPORT_MAPPING_VERSION,
            "checksum": checksum,
            "mapping": {
                "strategy": "HEADER_LABEL_DETECTION",
                "sheet": rows[0].get("_source_sheet") if rows else None,
            },
            "rows": preview_rows,
            "previousImportId": prior.id if prior else None,
            "accepted": 0,
            "rejected": [],
        }
    if prior:
        result = json.loads(prior.result_json)
        result["idempotent"] = True
        result["importJobId"] = prior.id
        return result
    if job_organization_id is None:
        raise HTTPException(
            status_code=422,
            detail="File không có doanh nghiệp nào khớp với dữ liệu hệ thống.",
        )

    created = 0
    updated = 0
    rejected: list[dict[str, Any]] = []
    for row, organization, existing in prepared:
        missing = [label for field, label in required_fields.items() if not row.get(field)]
        if row.get("_invalid_crew_role"):
            missing.append("Chức danh hợp lệ")
        if row.get("organization_name") and not organization:
            missing.append("Doanh nghiệp đã có trong hệ thống")
        if missing:
            rejected.append({
                "sourceRow": row.get("_source_row"),
                "row": row.get("full_name"),
                "error": f"Thiếu hoặc không hợp lệ: {', '.join(missing)}",
            })
            continue
        data = {
            key: value for key, value in row.items()
            if not key.startswith("_") and key != "organization_name" and hasattr(CrewMember, key)
        }
        data["organization_id"] = organization.id
        data["vessel_id"] = None
        data["updated_at"] = now_iso()
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            existing.version += 1
            member = existing
            updated += 1
            action = "IMPORT_UPDATE"
        else:
            data["created_at"] = now_iso()
            member = CrewMember(**data)
            db.add(member)
            created += 1
            action = "IMPORT_CREATE"
        db.flush()
        audit(
            db, "CREW", member.id, action, f"{member.full_name} / {member.crew_role}",
            actor_user_id=user.id, organization_id=organization.id,
            reporting_unit_id=scope.reporting_unit_id,
        )

    result = {
        "accepted": created + updated,
        "created": created,
        "updated": updated,
        "rejected": rejected,
        "mappingVersion": IMPORT_MAPPING_VERSION,
        "checksum": checksum,
        "idempotent": False,
    }
    job = ImportJob(
        organization_id=job_organization_id,
        reporting_unit_id=scope.reporting_unit_id,
        import_kind="CREW",
        source_checksum=checksum,
        mapping_version=IMPORT_MAPPING_VERSION,
        accepted_count=result["accepted"],
        rejected_count=len(rejected),
        result_json=json.dumps(result, ensure_ascii=False),
        created_by_user_id=user.id,
        created_at=now_iso(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    result["importJobId"] = job.id
    return result


@router.post("/api/import/declaration")
async def import_declaration(
    request: Request,
    preview: bool = False,
    db: Session = Depends(get_db),
    scope: Scope = Depends(resolve_scope),
):
    user = scope.user
    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="File trống.")
    validate_attachment_content(".xlsx", content)
    try:
        sheets = read_workbook(content)
        row = declaration_row(sheets)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Lỗi đọc file: {exc}")

    checksum = hashlib.sha256(content).hexdigest()
    if preview:
        return {
            "preview": True,
            "mappingVersion": IMPORT_MAPPING_VERSION,
            "checksum": checksum,
            "row": row,
            "accepted": 0,
            "rejected": [],
        }
    row["created_at"] = now_iso()
    row["updated_at"] = now_iso()
    # Import rows keep the IMP marker and a microsecond tail for uniqueness in
    # bulk (they are not the per-day human sequence used for manual entry).
    row["reference_no"] = f"TT-IMP-{datetime.now():%y%m%d}-{datetime.now().microsecond:06d}"
    row["workflow_status"] = "DRAFT"
    row["status"] = "DRAFT"
    row["unload_json"] = json.dumps(cargo(row.pop("unload", {})), ensure_ascii=False)
    row["load_json"] = json.dumps(cargo(row.pop("load", {})), ensure_ascii=False)

    safe = {k: v for k, v in row.items() if not k.startswith("_") and hasattr(Declaration, k)}
    imported_company_name = str(safe.get("company_name") or "").strip()
    if not safe.get("declaration_date"):
        safe["declaration_date"] = date.today().isoformat()
    for required in ("company_name", "vessel_name", "registration_no", "vessel_type",
                     "vessel_class", "last_port", "working_port", "eta", "etd",
                     "master_name", "master_phone"):
        if not safe.get(required):
            safe[required] = "N/A"

    # CUSTOMER imports stay tenant-bound. PLATFORM_ADMIN may import a declaration sent by
    # any customer inside its resolved reporting unit; the workbook company name
    # selects (or creates) the tenant.
    if scope.is_customer:
        target_organization = user.organization
    else:
        if not imported_company_name:
            raise HTTPException(status_code=422, detail="File phải có tên doanh nghiệp để Admin nhập phiếu khai báo.")
        target_organization = _import_organization(db, imported_company_name)
        if target_organization is None:
            # Brand-new Organization: onboard it through this resolved unit.
            target_organization = _get_or_create_org(db, imported_company_name)
            db.add(ReportingUnitOrganization(
                reporting_unit_id=scope.reporting_unit_id, organization_id=target_organization.id,
                created_at=now_iso(),
            ))
        else:
            scope.require_org(target_organization.id)
    if target_organization is None:
        raise HTTPException(status_code=422, detail="File phải có tên doanh nghiệp để Admin nhập phiếu khai báo.")

    target_organization_id = target_organization.id
    safe["organization_id"] = target_organization_id

    prior = db.query(ImportJob).filter(
        ImportJob.organization_id == target_organization_id,
        ImportJob.reporting_unit_id == (scope.reporting_unit_id if scope.is_port else None),
        ImportJob.import_kind == "DECLARATION",
        ImportJob.source_checksum == checksum,
        ImportJob.mapping_version == IMPORT_MAPPING_VERSION,
    ).first()
    if prior:
        result = json.loads(prior.result_json)
        result["idempotent"] = True
        result["importJobId"] = prior.id
        return result

    remove_demo_data_for_real_input(
        db,
        retain_organization_id=target_organization_id,
        organization_data={"name": imported_company_name},
        allowed_organization_ids=scope.member_org_ids if scope.is_port else None,
    )
    safe["company_name"] = target_organization.name

    decl = Declaration(**safe)
    db.add(decl)
    db.flush()
    audit(
        db, "DECLARATION", decl.id, "IMPORT_CREATE", decl.reference_no,
        actor_user_id=user.id, organization_id=target_organization_id,
        reporting_unit_id=scope.reporting_unit_id if scope.is_port else None,
    )
    result = {
        "accepted": 1, "rejected": [], "id": decl.id,
        "mappingVersion": IMPORT_MAPPING_VERSION, "checksum": checksum,
        "idempotent": False,
    }
    job = ImportJob(
        organization_id=target_organization_id, import_kind="DECLARATION",
        reporting_unit_id=scope.reporting_unit_id if scope.is_port else None,
        source_checksum=checksum, mapping_version=IMPORT_MAPPING_VERSION,
        accepted_count=1, rejected_count=0,
        result_json=json.dumps(result, ensure_ascii=False),
        created_by_user_id=user.id, created_at=now_iso(),
    )
    db.add(job)
    db.commit()
    db.refresh(decl)
    db.refresh(job)
    result["importJobId"] = job.id
    return result




