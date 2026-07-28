"""Helper và hằng số dùng chung giữa app.py và các module router tách ra.

Tồn tại để các module router (reports_api, import_api, ...) không phải import
ngược từ app.py — vòng phụ thuộc đó là thứ historical_api.py đã tránh được từ
đầu. Chỉ chứa thứ KHÔNG phụ thuộc vào đối tượng `app`; những gì chỉ một nơi
dùng thì để nguyên tại chỗ, không gom vào đây.
"""
from __future__ import annotations

from datetime import date
from typing import Any, List, Optional

from fastapi import HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from .database import DEMO_ORGANIZATION_TAX_CODE, ROOT, now_iso
from .logging_config import configure_local_logging
from .models import (
    Attachment, AuditEvent, CrewMember, Declaration, DeclarationCrew,
    DeclarationEvent, ImportJob, Organization, ReportingUnitOrganization, User,
    Vessel, VesselOperatingProfile,
)
from .tenant import Scope
from .xlsx_io import import_match_key


IMPORT_MAPPING_VERSION = "KBCV-IMPORT-1.5"
CREW_ROLES = ("Thuyền trưởng", "Máy trưởng", "Thuyền viên", "Thuyền phó")
CREW_ROLE_CANONICAL = {import_match_key(role): role for role in CREW_ROLES}

# Logger ghi access log cục bộ. Khởi tạo một lần tại đây (không phải trong
# app.py) để mọi module router dùng chung đúng một handler — gọi
# configure_local_logging nhiều lần sẽ gắn thêm handler trùng lặp.
access_logger = configure_local_logging(ROOT)


def _clean_email(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if "@" not in value or " " in value or len(value) > 200:
        raise ValueError("Email không hợp lệ.")
    return value


def certificate_status(value: Optional[str], warning_days: int = 30) -> str:
    if not value:
        return "UNKNOWN"
    try:
        expiry = date.fromisoformat(value[:10])
    except ValueError:
        return "UNKNOWN"
    remaining = (expiry - date.today()).days
    if remaining < 0:
        return "EXPIRED"
    if remaining <= warning_days:
        return "EXPIRING"
    return "VALID"


# ── Attachment signature rules ─────────────────────────────────────────────────
MAGIC_BYTES: dict[str, bytes] = {
    ".pdf": b"%PDF",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".png": b"\x89PNG",
    ".xlsx": b"PK\x03\x04",
    ".xls": b"\xd0\xcf",
    ".doc": b"\xd0\xcf",
    ".docx": b"PK\x03\x04",
    ".webp": b"RIFF",
}
ALLOWED_ATTACHMENT_EXTENSIONS = frozenset(MAGIC_BYTES)
MAX_ATTACHMENT_BYTES = 12 * 1024 * 1024  # 12 MB


def validate_attachment_content(extension: str, content: bytes) -> None:
    extension = extension.lower()
    if extension not in ALLOWED_ATTACHMENT_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Phần mở rộng file không được hỗ trợ.")
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=413, detail="File vượt quá giới hạn 12 MB.")
    expected = MAGIC_BYTES[extension]
    if not content.startswith(expected):
        raise HTTPException(
            status_code=400,
            detail=f"File không đúng định dạng {extension} (magic bytes không khớp).",
        )


class VesselOperatingProfilePayload(BaseModel):
    sequence: int = 1
    activity_area: str
    deadweight_tons: Optional[float] = None
    cargo_capacity_tons: Optional[float] = None

    @field_validator("activity_area")
    @classmethod
    def required_activity_area(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Vùng hoạt động là bắt buộc.")
        return value

    @field_validator("deadweight_tons", "cargo_capacity_tons")
    @classmethod
    def non_negative_profile_value(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value < 0:
            raise ValueError("Thông số vùng hoạt động không được âm.")
        return value


def _sync_vessel_operating_profiles(
    vessel: Vessel,
    profiles: Optional[List[VesselOperatingProfilePayload | dict[str, Any]]],
) -> None:
    if profiles is None:
        return
    vessel.operating_profiles.clear()
    normalized: list[dict[str, Any]] = []
    for index, profile in enumerate(profiles, start=1):
        values = profile.model_dump() if isinstance(profile, BaseModel) else profile
        activity_area = str(values.get("activity_area") or "").strip()
        if not activity_area:
            continue
        item = {
            "sequence": index,
            "activity_area": activity_area,
            "deadweight_tons": values.get("deadweight_tons"),
            "cargo_capacity_tons": values.get("cargo_capacity_tons"),
        }
        normalized.append(item)
        vessel.operating_profiles.append(VesselOperatingProfile(**item))
    if normalized:
        vessel.vessel_class = " / ".join(item["activity_area"] for item in normalized)
        vessel.deadweight_tons = normalized[0]["deadweight_tons"]
        vessel.cargo_capacity_tons = normalized[0]["cargo_capacity_tons"]


def _get_or_create_org(db: Session, name: Optional[str]) -> Optional[Organization]:
    if not name:
        return None
    org = db.query(Organization).filter(Organization.name == name).first()
    if not org:
        org = Organization(name=name, updated_at=now_iso(), created_at=now_iso())
        db.add(org)
        db.flush()
    return org


def _resolve_org_for_port_scope(db: Session, scope: Scope, name: Optional[str]) -> Optional[Organization]:
    """Look up or create an Organization by name for a PORT-scope mutation.

    A brand-new Organization is onboarded through (and linked to) the resolved
    reporting unit. An Organization that already exists must already belong to
    the resolved unit — otherwise it is another tenant's data and is rejected.
    """
    if not name:
        return None
    org = db.query(Organization).filter(Organization.name == name).first()
    if org is None:
        org = Organization(name=name, updated_at=now_iso(), created_at=now_iso())
        db.add(org)
        db.flush()
        db.add(ReportingUnitOrganization(
            reporting_unit_id=scope.reporting_unit_id, organization_id=org.id, created_at=now_iso(),
        ))
        return org
    if org.id not in scope.member_org_ids:
        raise HTTPException(status_code=403, detail="Tổ chức không thuộc đơn vị báo cáo hiện tại.")
    return org


def remove_demo_data_for_real_input(
    db: Session,
    *,
    retain_organization_id: int | None = None,
    organization_data: dict[str, Any] | None = None,
    allowed_organization_ids: tuple[int, ...] | None = None,
) -> bool:
    """Remove sentinel-marked records before the first real input.

    A demo CUSTOMER keeps its organization binding, but the sentinel is cleared
    and optional workbook metadata becomes the real profile. PLATFORM_ADMIN imports may
    remove the demo organization entirely.
    """
    demo_org = db.query(Organization).filter(
        Organization.tax_code == DEMO_ORGANIZATION_TAX_CODE
    ).first()
    if not demo_org:
        return False
    if allowed_organization_ids is not None and demo_org.id not in allowed_organization_ids:
        return False

    declaration_ids = [row[0] for row in db.query(Declaration.id).filter(
        Declaration.organization_id == demo_org.id
    ).all()]
    if declaration_ids:
        db.query(Attachment).filter(Attachment.declaration_id.in_(declaration_ids)).delete(synchronize_session=False)
        db.query(DeclarationCrew).filter(DeclarationCrew.declaration_id.in_(declaration_ids)).delete(synchronize_session=False)
        db.query(DeclarationEvent).filter(DeclarationEvent.declaration_id.in_(declaration_ids)).delete(synchronize_session=False)
        db.query(Declaration).filter(Declaration.id.in_(declaration_ids)).delete(synchronize_session=False)
    db.query(CrewMember).filter(CrewMember.organization_id == demo_org.id).delete(synchronize_session=False)
    db.query(Vessel).filter(Vessel.organization_id == demo_org.id).delete(synchronize_session=False)
    db.query(AuditEvent).filter(AuditEvent.organization_id == demo_org.id).delete(synchronize_session=False)
    db.query(ImportJob).filter(ImportJob.organization_id == demo_org.id).delete(synchronize_session=False)
    if retain_organization_id == demo_org.id:
        profile = organization_data or {}
        proposed_name = str(profile.get("name") or "").strip()
        name_in_use = proposed_name and db.query(Organization.id).filter(
            Organization.name == proposed_name, Organization.id != demo_org.id
        ).first()
        if proposed_name and not name_in_use:
            demo_org.name = proposed_name
        demo_org.tax_code = str(profile.get("tax_code") or "").strip()
        for field in ("address", "contact_name", "phone"):
            value = str(profile.get(field) or "").strip()
            if value:
                setattr(demo_org, field, value)
        demo_org.updated_at = now_iso()
    else:
        db.query(User).filter(User.organization_id == demo_org.id).update(
            {User.organization_id: None}, synchronize_session=False
        )
        db.delete(demo_org)
    db.flush()
    return True
