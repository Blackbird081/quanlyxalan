"""Reporting-unit, port-register, and vessel API routes.

Extracted from backend.app without changing route methods, paths, endpoint
names, dependencies, or response behavior. This module must stay below app.py
in the dependency graph and must never import backend.app.
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, field_validator
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from .database import audit, get_db, joined_profile_value, now_iso
from .integrations import registry_adapter
from .models import (
    Attachment, CrewMember, Declaration, Organization, ReportingUnit,
    ReportingUnitUser, ReportingUnitVessel, User, Vessel,
)
from .rbac import require_roles
from .shared import (
    VesselOperatingProfilePayload, _clean_email, _get_or_create_org,
    _resolve_org_for_port_scope, _sync_vessel_operating_profiles,
    certificate_status, remove_demo_data_for_real_input,
    validate_attachment_content,
)
from .storage import ScannerNotConfigured, get_attachment_storage
from .tenant import (
    Scope, register_vessel_ids, require_port_scope, require_vessel_in_scope,
    resolve_scope,
)
from .xlsx_io import make_xlsx


router = APIRouter()
ROOT = Path(__file__).resolve().parents[1]
attachment_storage = get_attachment_storage(ROOT / "data" / "attachments" / "quarantine")
attachment_scanner = ScannerNotConfigured()
logger = logging.getLogger(__name__)


class ReportingUnitCreateRequest(BaseModel):
    name: str
    code: str
    notify_email: str = ""  # email chung của Cảng để nhận thông báo (tùy chọn)

    @field_validator("notify_email")
    @classmethod
    def valid_notify_email(cls, value: str) -> str:
        return _clean_email(value)

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        value = " ".join(value.strip().split())
        if len(value) < 2 or len(value) > 150:
            raise ValueError("Tên đơn vị phải có từ 2 đến 150 ký tự.")
        return value

    @field_validator("code")
    @classmethod
    def valid_code(cls, value: str) -> str:
        value = "-".join(value.strip().upper().split())
        if len(value) < 2 or len(value) > 30:
            raise ValueError("Mã đơn vị phải có từ 2 đến 30 ký tự.")
        if any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in value):
            raise ValueError("Mã đơn vị chỉ dùng chữ A-Z, số, dấu gạch ngang hoặc gạch dưới.")
        return value


class VesselSaveRequest(BaseModel):
    id: Optional[int] = None
    version: Optional[int] = None
    organization_name: Optional[str] = None
    organization: Optional[Dict[str, Any]] = None
    name: str
    registration_no: str
    registry_or_imo: str = ""
    vessel_type: str
    vessel_category: Optional[str] = None
    vessel_class: str
    shell_material: str = ""
    build_year: Optional[int] = None
    length_m: Optional[float] = None
    width_m: Optional[float] = None
    side_height_m: Optional[float] = None
    draft_m: Optional[float] = None
    deadweight_tons: Optional[float] = None
    gross_tonnage: Optional[float] = None
    engine_power_cv: Optional[float] = None
    cargo_capacity_tons: Optional[float] = None
    container_capacity_teu: Optional[float] = None
    passenger_capacity: Optional[int] = None
    min_crew: Optional[int] = None
    safety_certificate_no: str = ""
    certificate_issue_date: Optional[str] = None
    certificate_expiry_date: Optional[str] = None
    tracking_master_name: str = ""
    tracking_master_phone: str = ""
    operating_profiles: Optional[List[VesselOperatingProfilePayload]] = None
    notes: str = ""

    @field_validator("name", "registration_no")
    @classmethod
    def required_vessel_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Trường này là bắt buộc.")
        return value

    @field_validator("length_m", "width_m", "side_height_m", "draft_m", "deadweight_tons", "gross_tonnage", "engine_power_cv", "cargo_capacity_tons", "container_capacity_teu")
    @classmethod
    def non_negative_measurements(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value < 0:
            raise ValueError("Thông số không được âm.")
        return value

    @field_validator("build_year", "passenger_capacity", "min_crew")
    @classmethod
    def non_negative_integer_fields(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise ValueError("Thông số không được âm.")
        return value


class PortRegisterRemoveRequest(BaseModel):
    ids: List[int]

    @field_validator("ids")
    @classmethod
    def valid_ids(cls, value: List[int]) -> List[int]:
        ids = list(dict.fromkeys(value))
        if not ids:
            raise ValueError("Cần chọn ít nhất một Salan.")
        if len(ids) > 100:
            raise ValueError("Mỗi lần chỉ được xử lý tối đa 100 Salan.")
        if any(item <= 0 for item in ids):
            raise ValueError("Mã Salan không hợp lệ.")
        return ids


class PortRegisterAddRequest(PortRegisterRemoveRequest):
    pass


# ══════════════════════════════════════════════════════════════════════════════
# VESSELS
# ══════════════════════════════════════════════════════════════════════════════

def _vessel_dict(v: Vessel) -> dict:
    d = {c.name: getattr(v, c.name) for c in v.__table__.columns}
    d["organization_name"] = v.organization.name if v.organization else None
    d["certificate_status"] = certificate_status(v.certificate_expiry_date)
    d["operating_profiles"] = [
        {
            "id": profile.id,
            "sequence": profile.sequence,
            "activity_area": profile.activity_area,
            "deadweight_tons": profile.deadweight_tons,
            "cargo_capacity_tons": profile.cargo_capacity_tons,
        }
        for profile in v.operating_profiles
    ]
    d["attachments"] = [_attachment_dict(item) for item in v.attachments]
    return d


def _attachment_dict(item: Attachment) -> dict[str, Any]:
    return {
        "id": item.id,
        "original_name": item.original_name,
        "content_type": item.content_type,
        "size_bytes": item.size_bytes,
        "checksum_sha256": item.checksum_sha256,
        "scan_status": item.scan_status,
        "storage_backend": item.storage_backend,
        "created_at": item.created_at,
    }




@router.get("/api/reporting-units")
def list_reporting_units(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("PORT_STAFF", "PLATFORM_ADMIN")),
):
    """Active reporting units the caller may select as tenant context.

    PORT_STAFF sees only units where it holds membership; PLATFORM_ADMIN sees all
    active units and must deliberately choose one before opening tenant data.
    """
    query = db.query(ReportingUnit).filter(ReportingUnit.is_active == 1)
    staff_functions: dict[int, str | None] = {}
    if user.role == "PORT_STAFF":
        memberships = db.query(ReportingUnitUser).filter_by(user_id=user.id).all()
        if not memberships:
            return {"items": [], "role": user.role}
        staff_functions = {m.reporting_unit_id: m.staff_function for m in memberships}
        query = query.filter(ReportingUnit.id.in_(staff_functions.keys()))
    units = query.order_by(ReportingUnit.name).all()
    return {
        "items": [
            {
                "id": u.id, "name": u.name, "code": u.code, "notify_email": u.notify_email or "",
                # None cho PLATFORM_ADMIN (không gate theo staff_function — full
                # authority ở mọi cổng, xem Scope.allows_staff_function).
                "staff_function": staff_functions.get(u.id) if user.role == "PORT_STAFF" else None,
            }
            for u in units
        ],
        "role": user.role,
    }


@router.post("/api/reporting-units", status_code=201)
def create_reporting_unit(
    payload: ReportingUnitCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    """Create an empty tenant. Memberships and customer links are separate.

    This is a platform operation and deliberately does not infer or copy the
    currently selected tenant's organizations, staff or historical data.
    """
    duplicate = db.query(ReportingUnit).filter(
        or_(
            func.lower(ReportingUnit.name) == payload.name.lower(),
            func.lower(ReportingUnit.code) == payload.code.lower(),
        )
    ).first()
    if duplicate:
        field = "tên" if duplicate.name.lower() == payload.name.lower() else "mã"
        raise HTTPException(status_code=409, detail=f"Đã có đơn vị báo cáo dùng {field} này.")
    item = ReportingUnit(
        name=payload.name, code=payload.code, official_header_json="{}",
        notify_email=payload.notify_email,
        is_active=1, created_at=now_iso(), updated_at=now_iso(),
    )
    db.add(item)
    db.flush()
    audit(
        db, "REPORTING_UNIT", item.id, "CREATE", f"{item.name} ({item.code})",
        actor_user_id=user.id, reporting_unit_id=item.id,
    )
    db.commit()
    db.refresh(item)
    return {
        "id": item.id, "name": item.name, "code": item.code,
        "notify_email": item.notify_email or "", "is_active": bool(item.is_active),
    }


@router.put("/api/reporting-units/{unit_id}")
def update_reporting_unit(
    unit_id: int,
    payload: ReportingUnitCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    """Update a reporting unit's name/code/notify_email (platform operation)."""
    item = db.query(ReportingUnit).filter(ReportingUnit.id == unit_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn vị báo cáo.")
    duplicate = db.query(ReportingUnit).filter(
        ReportingUnit.id != unit_id,
        or_(
            func.lower(ReportingUnit.name) == payload.name.lower(),
            func.lower(ReportingUnit.code) == payload.code.lower(),
        ),
    ).first()
    if duplicate:
        field = "tên" if duplicate.name.lower() == payload.name.lower() else "mã"
        raise HTTPException(status_code=409, detail=f"Đã có đơn vị báo cáo khác dùng {field} này.")
    item.name = payload.name
    item.code = payload.code
    item.notify_email = payload.notify_email
    item.updated_at = now_iso()
    audit(
        db, "REPORTING_UNIT", item.id, "UPDATE", f"{item.name} ({item.code})",
        actor_user_id=user.id, reporting_unit_id=item.id,
    )
    db.commit()
    db.refresh(item)
    return {
        "id": item.id, "name": item.name, "code": item.code,
        "notify_email": item.notify_email or "", "is_active": bool(item.is_active),
    }


@router.get("/api/reporting-unit/organizations")
def list_reporting_unit_organizations(
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    if not scope.member_org_ids:
        return {"items": []}
    organizations = (
        db.query(Organization)
        .filter(Organization.id.in_(scope.member_org_ids))
        .order_by(Organization.name, Organization.id)
        .all()
    )
    return {"items": [{"id": item.id, "name": item.name} for item in organizations]}


@router.get("/api/vessels")
def get_vessels(db: Session = Depends(get_db), scope: Scope = Depends(resolve_scope)):
    # Reads are scoped: CUSTOMER to its Organization; PORT to the Organizations
    # linked to the resolved reporting unit. Never a global fetch.
    org_ids = scope.visible_org_ids()
    if not org_ids:
        return []
    vessels = (
        db.query(Vessel)
        .filter(Vessel.organization_id.in_(org_ids))
        .order_by(Vessel.name, Vessel.registration_no)
        .all()
    )
    return [_vessel_dict(v) for v in vessels]


# joined_profile_value đã chuyển sang backend/database.py (reports_api.py cũng
# dùng) và được import ở đầu file này.


@router.get("/api/port-vessel-register")
def get_port_vessel_register(
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    register_ids = register_vessel_ids(db, scope.reporting_unit_id)
    vessels = (
        db.query(Vessel)
        .filter(Vessel.id.in_(register_ids))
        .order_by(Vessel.name, Vessel.registration_no)
        .all()
    ) if register_ids else []

    # "Lượt gần nhất" — chỉ tham khảo, KHÔNG chuyển record giữa 2 tab (quyết
    # định nghiệp vụ đã chốt, xem ROADMAP_PORT_OPERATIONS.md Giai đoạn 3). Sổ
    # theo dõi lưu theo phương tiện (vĩnh viễn); Declaration là theo lượt.
    latest_calls: dict[int, dict] = {}
    if register_ids:
        recent = (
            db.query(Declaration)
            .filter(Declaration.vessel_id.in_(register_ids))
            # updated_at only has second precision — id DESC as tiebreak makes
            # "most recent" deterministic even when two saves land in the same second.
            .order_by(Declaration.vessel_id, Declaration.updated_at.desc(), Declaration.id.desc())
            .all()
        )
        for declaration in recent:
            if declaration.vessel_id not in latest_calls:
                latest_calls[declaration.vessel_id] = {
                    "reference_no": declaration.reference_no,
                    "workflow_status": declaration.workflow_status,
                    "actual_departure_at": declaration.actual_departure_at,
                    "updated_at": declaration.updated_at,
                }

    profile_count = sum(len(vessel.operating_profiles) for vessel in vessels)
    multi_area_count = sum(len(vessel.operating_profiles) > 1 for vessel in vessels)
    certificate_warnings = sum(
        certificate_status(vessel.certificate_expiry_date) in {"EXPIRING", "EXPIRED"}
        for vessel in vessels
    )
    teu_capacity = sum(vessel.container_capacity_teu or 0 for vessel in vessels)
    # Cộng theo từng dòng operating_profiles (không phải vessel.cargo_capacity_tons,
    # vốn chỉ giữ giá trị của vùng đầu tiên) để không bỏ sót năng lực vùng thứ hai
    # của Salan hoạt động cả VR-SI lẫn VR-SII.
    tonnage_capacity = sum(
        profile.cargo_capacity_tons or 0
        for vessel in vessels
        for profile in vessel.operating_profiles
    )
    area_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    for vessel in vessels:
        type_counts[vessel.vessel_type] = type_counts.get(vessel.vessel_type, 0) + 1
        # Mỗi Salan tính đúng một lần: vùng đơn giữ nguyên nhãn, vùng kép gộp
        # thành một dòng riêng (vd "VR-SI / VR-SII") thay vì cộng trùng vào cả
        # hai thanh — nếu không tổng các thanh sẽ vượt quá tổng số Salan.
        areas = sorted({profile.activity_area for profile in vessel.operating_profiles if profile.activity_area})
        if not areas:
            continue
        label = " / ".join(areas)
        area_counts[label] = area_counts.get(label, 0) + 1
    items = []
    for vessel in vessels:
        item = _vessel_dict(vessel)
        item["latest_call"] = latest_calls.get(vessel.id)
        items.append(item)

    return {
        "items": items,
        "stats": {
            "vessels": len(vessels),
            "operatingProfiles": profile_count,
            "multiAreaVessels": multi_area_count,
            "certificateWarnings": certificate_warnings,
            "teuCapacity": teu_capacity,
            "tonnageCapacity": tonnage_capacity,
        },
        "byArea": [
            {"label": label, "value": value}
            for label, value in sorted(area_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
        "byType": [
            {"label": label, "value": value}
            for label, value in sorted(type_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
    }


@router.get("/api/port-vessel-register/export")
def export_port_vessel_register(
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    register_ids = register_vessel_ids(db, scope.reporting_unit_id)
    vessels = (
        db.query(Vessel)
        .filter(Vessel.id.in_(register_ids))
        .order_by(Vessel.name, Vessel.registration_no)
        .all()
    ) if register_ids else []
    headers = [
        "STT", "TÊN PHƯƠNG TIỆN", "SỐ ĐĂNG KÝ", "LOẠI PHƯƠNG TIỆN (CÔNG DỤNG)",
        "CẤP PT (VÙNG HOẠT ĐỘNG)", "CHIỀU DÀI (M)", "TRỌNG TẢI TOÀN PHẦN (TẤN)",
        "DUNG TÍCH (M3)", "KHẢ NĂNG KHAI THÁC (TẤN)", "KHẢ NĂNG KHAI THÁC (TEU)",
        "NGÀY HẾT HẠN GCNATKT&BVMT", "SỐ THUYỀN VIÊN", "THUYỀN TRƯỞNG",
        "SỐ ĐIỆN THOẠI LIÊN HỆ",
    ]
    rows = []
    for index, vessel in enumerate(vessels, start=1):
        areas = [profile.activity_area for profile in vessel.operating_profiles if profile.activity_area]
        rows.append([
            index,
            vessel.name,
            vessel.registration_no,
            vessel.vessel_type,
            " / ".join(areas) if areas else vessel.vessel_class,
            vessel.length_m,
            joined_profile_value(vessel, "deadweight_tons"),
            vessel.gross_tonnage,
            joined_profile_value(vessel, "cargo_capacity_tons"),
            vessel.container_capacity_teu,
            vessel.certificate_expiry_date or "",
            vessel.min_crew,
            vessel.tracking_master_name,
            vessel.tracking_master_phone,
        ])
    content = make_xlsx("DỮ LIỆU SÀ LAN", headers, rows)
    filename = f"DU_LIEU_SA_LAN_{date.today().isoformat()}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/api/port-vessel-register/remove")
def remove_from_port_vessel_register(
    payload: PortRegisterRemoveRequest,
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    """Remove rows from THIS reporting unit's register without deleting masters."""
    register_ids = set(register_vessel_ids(db, scope.reporting_unit_id))
    missing_ids = [item for item in payload.ids if item not in register_ids]
    if missing_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy Salan đang được theo dõi: {', '.join(map(str, missing_ids))}.",
        )

    updated_at = now_iso()
    removed = 0
    for vessel_id in payload.ids:
        link = (
            db.query(ReportingUnitVessel)
            .filter_by(reporting_unit_id=scope.reporting_unit_id, vessel_id=vessel_id)
            .first()
        )
        if link is None:
            continue
        vessel = db.get(Vessel, vessel_id)
        db.delete(link)
        # Legacy compatibility flag: clear only when no unit tracks it anymore.
        if vessel is not None:
            still_tracked = (
                db.query(ReportingUnitVessel).filter_by(vessel_id=vessel_id).count() > 1
            )
            if not still_tracked:
                vessel.is_port_tracked = 0
            vessel.port_tracking_updated_at = updated_at
            vessel.updated_at = updated_at
            vessel.version += 1
        audit(
            db, "VESSEL", vessel_id, "PORT_REGISTER_REMOVE",
            (vessel.name + " / " + vessel.registration_no) if vessel else str(vessel_id),
            actor_user_id=scope.user.id,
            organization_id=vessel.organization_id if vessel else None,
            reporting_unit_id=scope.reporting_unit_id,
        )
        removed += 1
    db.commit()
    return {"removed": removed, "ids": payload.ids}


@router.post("/api/port-vessel-register/add")
def add_to_port_vessel_register(
    payload: PortRegisterAddRequest,
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    """Link existing Vessel masters to this unit without changing ownership."""
    vessels = db.query(Vessel).filter(Vessel.id.in_(payload.ids)).all()
    by_id = {vessel.id: vessel for vessel in vessels}
    missing_ids = [item for item in payload.ids if item not in by_id]
    if missing_ids:
        raise HTTPException(status_code=404, detail="Không tìm thấy phương tiện cần thêm vào sổ.")
    added = 0
    timestamp = now_iso()
    for vessel_id in payload.ids:
        if db.query(ReportingUnitVessel).filter_by(
            reporting_unit_id=scope.reporting_unit_id, vessel_id=vessel_id,
        ).first() is not None:
            continue
        vessel = by_id[vessel_id]
        db.add(ReportingUnitVessel(
            reporting_unit_id=scope.reporting_unit_id,
            vessel_id=vessel_id,
            added_by_user_id=scope.user.id,
            created_at=timestamp,
        ))
        vessel.is_port_tracked = 1
        vessel.port_tracking_updated_at = timestamp
        vessel.updated_at = timestamp
        vessel.version += 1
        audit(
            db, "VESSEL", vessel_id, "PORT_REGISTER_ADD",
            f"{vessel.name} / {vessel.registration_no}",
            actor_user_id=scope.user.id,
            organization_id=vessel.organization_id,
            reporting_unit_id=scope.reporting_unit_id,
        )
        added += 1
    db.commit()
    return {"added": added, "ids": payload.ids}


@router.post("/api/vessels")
def save_vessel(
    payload: VesselSaveRequest,
    port_register: bool = False,
    db: Session = Depends(get_db),
    scope: Scope = Depends(resolve_scope),
):
    user = scope.user
    if port_register and scope.is_customer:
        raise HTTPException(status_code=403, detail="Sổ theo dõi Salan chỉ dành cho Nhân viên Cảng và Admin.")
    if scope.is_customer:
        # Force organization to the customer's bound organization
        org_id = user.organization_id
    else:
        # PLATFORM_ADMIN/PORT_STAFF can specify organization name
        org_name = (
            (payload.organization or {}).get("name") if isinstance(payload.organization, dict)
            else payload.organization_name
        )
        if port_register:
            # The internal register is vessel-scoped and Organization-agnostic:
            # it may reference any Organization's vessel.
            org = _get_or_create_org(db, org_name)
        else:
            org = _resolve_org_for_port_scope(db, scope, org_name)
        org_id = org.id if org else None

    if not payload.id:
        remove_demo_data_for_real_input(
            db,
            retain_organization_id=org_id if scope.is_customer else None,
            organization_data=payload.organization if isinstance(payload.organization, dict) else None,
            allowed_organization_ids=scope.member_org_ids if scope.is_port else None,
        )

    data = payload.model_dump(
        exclude={"id", "version", "organization", "organization_name", "operating_profiles"}
    )
    data["organization_id"] = org_id
    data["updated_at"] = now_iso()
    if port_register:
        data["is_port_tracked"] = 1
        data["port_tracking_updated_at"] = data["updated_at"]

    audit_unit_id = scope.reporting_unit_id if scope.is_port else None
    if payload.id:
        vessel = db.query(Vessel).filter(Vessel.id == payload.id).first()
        if not vessel:
            raise HTTPException(status_code=404, detail="Không tìm thấy phương tiện.")
        if payload.version is not None and payload.version != vessel.version:
            raise HTTPException(status_code=409, detail="Hồ sơ phương tiện đã được cập nhật bởi người dùng khác.")
        # Tenant isolation check (customer org ownership or in-unit vessel/register).
        require_vessel_in_scope(db, scope, vessel)

        for k, v in data.items():
            if hasattr(vessel, k):
                setattr(vessel, k, v)
        _sync_vessel_operating_profiles(vessel, payload.operating_profiles)
        vessel.version += 1
        audit(
            db, "VESSEL", vessel.id, "UPDATE", f"{vessel.name} / {vessel.registration_no}",
            actor_user_id=user.id, organization_id=vessel.organization_id,
            reporting_unit_id=audit_unit_id,
        )
    else:
        data["created_at"] = now_iso()
        vessel = Vessel(**{k: v for k, v in data.items() if hasattr(Vessel, k)})
        db.add(vessel)
        db.flush()
        profiles = payload.operating_profiles
        if profiles is None and vessel.vessel_class:
            profiles = [VesselOperatingProfilePayload(
                activity_area=vessel.vessel_class,
                deadweight_tons=vessel.deadweight_tons,
                cargo_capacity_tons=vessel.cargo_capacity_tons,
            )]
        _sync_vessel_operating_profiles(vessel, profiles)
        audit(
            db, "VESSEL", vessel.id, "CREATE", f"{vessel.name} / {vessel.registration_no}",
            actor_user_id=user.id, organization_id=vessel.organization_id,
            reporting_unit_id=audit_unit_id,
        )

    # Internal register add is tenant-scoped through reporting_unit_vessels.
    if port_register and scope.is_port:
        exists = (
            db.query(ReportingUnitVessel)
            .filter_by(reporting_unit_id=scope.reporting_unit_id, vessel_id=vessel.id)
            .first()
        )
        if exists is None:
            db.add(ReportingUnitVessel(
                reporting_unit_id=scope.reporting_unit_id, vessel_id=vessel.id,
                added_by_user_id=user.id, created_at=now_iso(),
            ))
    db.commit()
    db.refresh(vessel)

    return _vessel_dict(vessel)


@router.get("/api/vessels/{vessel_id}/attachments")
def list_vessel_attachments(
    vessel_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(resolve_scope),
):
    vessel = db.query(Vessel).filter(Vessel.id == vessel_id).first()
    if not vessel:
        raise HTTPException(status_code=404, detail="Không tìm thấy phương tiện.")
    require_vessel_in_scope(db, scope, vessel)
    return [_attachment_dict(item) for item in vessel.attachments]


@router.post("/api/vessels/{vessel_id}/attachments")
async def upload_vessel_attachment(
    vessel_id: int,
    filename: str,
    request: Request,
    db: Session = Depends(get_db),
    scope: Scope = Depends(resolve_scope),
):
    vessel = db.query(Vessel).filter(Vessel.id == vessel_id).first()
    if not vessel:
        raise HTTPException(status_code=404, detail="Không tìm thấy phương tiện.")
    require_vessel_in_scope(db, scope, vessel)

    content = await request.body()
    extension = Path(filename).suffix.lower()
    validate_attachment_content(extension, content)
    safe_name = f"vessel_{vessel_id}_{uuid.uuid4().hex}{extension}"
    stored_name = attachment_storage.put_quarantined(safe_name, content)
    try:
        scan_status = attachment_scanner.scan(stored_name)
        item = Attachment(
            vessel_id=vessel_id,
            original_name=Path(filename).name[:255],
            stored_name=stored_name,
            content_type=request.headers.get("content-type", "application/octet-stream"),
            size_bytes=len(content),
            checksum_sha256=hashlib.sha256(content).hexdigest(),
            scan_status=scan_status,
            storage_backend=attachment_storage.backend_name,
            created_at=now_iso(),
        )
        db.add(item)
        db.flush()
        audit(
            db, "VESSEL_ATTACHMENT", item.id, "UPLOAD",
            f"vessel={vessel_id}; file={item.original_name}; bytes={item.size_bytes}",
            actor_user_id=scope.user.id, organization_id=vessel.organization_id,
            reporting_unit_id=scope.reporting_unit_id if scope.is_port else None,
        )
        db.commit()
    except Exception:
        db.rollback()
        try:
            attachment_storage.delete(stored_name)
        except Exception:
            # Preserve the original scanner/database exception while retaining
            # evidence that compensating storage cleanup itself failed.
            logger.exception("Unable to remove orphaned vessel attachment %s", stored_name)
        raise
    db.refresh(item)
    return _attachment_dict(item)


@router.delete("/api/vessels/{vessel_id}/attachments/{attachment_id}")
def delete_vessel_attachment(
    vessel_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(resolve_scope),
):
    vessel = db.query(Vessel).filter(Vessel.id == vessel_id).first()
    if not vessel:
        raise HTTPException(status_code=404, detail="Không tìm thấy phương tiện.")
    require_vessel_in_scope(db, scope, vessel)
    item = db.query(Attachment).filter_by(id=attachment_id, vessel_id=vessel_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy file đính kèm.")
    stored_name = item.stored_name
    original_name = item.original_name
    audit(
        db, "VESSEL_ATTACHMENT", item.id, "DELETE",
        f"vessel={vessel_id}; file={item.original_name}",
        actor_user_id=scope.user.id, organization_id=vessel.organization_id,
        reporting_unit_id=scope.reporting_unit_id if scope.is_port else None,
    )
    db.delete(item)
    db.commit()
    storage_deleted = True
    try:
        attachment_storage.delete(stored_name)
    except Exception:
        storage_deleted = False
        audit(
            db, "VESSEL_ATTACHMENT", attachment_id, "STORAGE_DELETE_PENDING",
            f"vessel={vessel_id}; file={original_name}; stored={stored_name}",
            actor_user_id=scope.user.id, organization_id=vessel.organization_id,
            reporting_unit_id=scope.reporting_unit_id if scope.is_port else None,
        )
        db.commit()
    return {
        "deleted": True,
        "id": attachment_id,
        "storageDeleted": storage_deleted,
        "storageCleanupPending": not storage_deleted,
    }


@router.delete("/api/vessels/{vessel_id}")
def delete_vessel(
    vessel_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    # Deletion is PLATFORM_ADMIN-only: PORT_STAFF keeps edit rights (fix wrong
    # fields) but a hard delete of a master vessel record is an admin action.
    if scope.user.role != "PLATFORM_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Chỉ Platform admin mới có quyền xóa hồ sơ phương tiện.",
        )
    vessel = db.query(Vessel).filter(Vessel.id == vessel_id).first()
    if not vessel:
        raise HTTPException(status_code=404, detail="Không tìm thấy phương tiện.")
    require_vessel_in_scope(db, scope, vessel)

    declaration_count = db.query(Declaration).filter(Declaration.vessel_id == vessel_id).count()
    if declaration_count:
        raise HTTPException(
            status_code=409,
            detail=f"Không thể xóa: phương tiện đang gắn với {declaration_count} phiếu khai báo. "
                   "Xóa các phiếu liên quan trước nếu chắc chắn cần xóa hồ sơ này.",
        )
    crew_count = db.query(CrewMember).filter(CrewMember.vessel_id == vessel_id).count()
    if crew_count:
        raise HTTPException(
            status_code=409,
            detail=f"Không thể xóa: phương tiện đang gắn với {crew_count} thuyền viên trong Danh sách thuyền viên. "
                   "Bỏ gán thuyền viên khỏi phương tiện này trước khi xóa.",
        )

    identity = f"{vessel.name} / {vessel.registration_no}"
    organization_id = vessel.organization_id
    audit_unit_id = scope.reporting_unit_id if scope.is_port else None
    db.delete(vessel)
    audit(
        db, "VESSEL", vessel_id, "DELETE", identity,
        actor_user_id=scope.user.id, organization_id=organization_id,
        reporting_unit_id=audit_unit_id,
    )
    db.commit()
    return {"deleted": vessel_id}


@router.post("/api/vessels/{vessel_id}/verify-registry")
def verify_vessel_registry(
    vessel_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(resolve_scope),
):
    """
    Local-only registry date check. Does NOT call any external Maritime Authority API.
    Records verification source as 'local' and updates certificate_status.
    External registry integration is out of scope until T6.
    """
    vessel = db.query(Vessel).filter(Vessel.id == vessel_id).first()
    if not vessel:
        raise HTTPException(status_code=404, detail="Không tìm thấy phương tiện.")

    # Tenant isolation check (customer org ownership or in-scope port vessel).
    require_vessel_in_scope(db, scope, vessel)

    adapter_status = registry_adapter().status()
    vessel.registry_verification_status = "VERIFIED_LOCAL"
    vessel.registry_verified_at = now_iso()
    vessel.registry_verification_source = "local"
    vessel.updated_at = now_iso()
    db.commit()
    db.refresh(vessel)
    result = _vessel_dict(vessel)
    result["adapter"] = adapter_status
    return result
