"""Platform-admin user-management, operations, and backup routes.

Extracted from backend.app without changing route methods, paths, endpoint
names, dependencies, or response behavior. This module must stay below app.py
in the dependency graph and must never import backend.app.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from scripts.backup_local import (
    BACKUP_GLOB,
    BACKUP_SUFFIX,
    backup as create_local_backup,
    prune as prune_local_backups,
)

from .auth import get_password_hash
from .database import (
    ROOT, SQLALCHEMY_DATABASE_URL, audit, engine, get_db, now_iso,
)
from .models import (
    Attachment, AuditEvent, Declaration, ImportJob, Organization, ReportingUnit,
    ReportingUnitUser, User, Vessel,
)
from .rbac import require_roles
from .shared import _clean_email, access_logger, certificate_status


BACKUP_DIR = ROOT / "data" / "backups"
router = APIRouter()


class UserCreateRequest(BaseModel):
    username: str
    password: str
    full_name: str = ""
    email: str = ""  # địa chỉ nhận thông báo (tùy chọn)
    role: str
    # CUSTOMER accounts must be tied to a customer Organization.
    organization_id: Optional[int] = None
    # PORT_STAFF accounts may be granted membership in one or more reporting units.
    reporting_unit_ids: List[int] = []

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        return _clean_email(value)

    @field_validator("username")
    @classmethod
    def valid_username(cls, value: str) -> str:
        value = value.strip().lower()
        if len(value) < 3 or len(value) > 50:
            raise ValueError("Tên đăng nhập phải có từ 3 đến 50 ký tự.")
        if any(char not in "abcdefghijklmnopqrstuvwxyz0123456789._-" for char in value):
            raise ValueError("Tên đăng nhập chỉ dùng chữ thường a-z, số, dấu chấm, gạch ngang hoặc gạch dưới.")
        return value

    @field_validator("password")
    @classmethod
    def valid_password(cls, value: str) -> str:
        if len(value) < 8 or len(value) > 128:
            raise ValueError("Mật khẩu phải có từ 8 đến 128 ký tự.")
        return value

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, value: str) -> str:
        return " ".join((value or "").strip().split())[:150]

    @field_validator("role")
    @classmethod
    def valid_role(cls, value: str) -> str:
        value = (value or "").strip().upper()
        if value not in {"CUSTOMER", "PORT_STAFF", "PLATFORM_ADMIN"}:
            raise ValueError("Vai trò không hợp lệ.")
        return value


class UserResetPasswordRequest(BaseModel):
    password: str

    @field_validator("password")
    @classmethod
    def valid_password(cls, value: str) -> str:
        if len(value) < 8 or len(value) > 128:
            raise ValueError("Mật khẩu phải có từ 8 đến 128 ký tự.")
        return value


class UserActiveRequest(BaseModel):
    is_active: bool


class UserUpdateRequest(BaseModel):
    """Admin editing another user's contact fields (not username/role/password)."""
    full_name: Optional[str] = None
    email: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return " ".join(value.strip().split())[:150]

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return _clean_email(value)


# ══════════════════════════════════════════════════════════════════════════════
# USER MANAGEMENT (PLATFORM_ADMIN)
# ══════════════════════════════════════════════════════════════════════════════

def _serialize_user(db: Session, item: User) -> dict:
    unit_rows = (
        db.query(ReportingUnit.id, ReportingUnit.name)
        .join(ReportingUnitUser, ReportingUnitUser.reporting_unit_id == ReportingUnit.id)
        .filter(ReportingUnitUser.user_id == item.id)
        .order_by(ReportingUnit.name)
        .all()
    )
    return {
        "id": item.id,
        "username": item.username,
        "full_name": item.full_name or "",
        "email": item.email or "",
        "role": item.role,
        "is_active": bool(item.is_active),
        "organization_id": item.organization_id,
        "organization_name": item.organization.name if item.organization else None,
        "reporting_units": [{"id": row[0], "name": row[1]} for row in unit_rows],
        "created_at": item.created_at,
    }


@router.get("/api/admin/users")
def list_users(
    db: Session = Depends(get_db), user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    users = db.query(User).order_by(User.role, User.username).all()
    return {"items": [_serialize_user(db, item) for item in users]}


@router.post("/api/admin/users", status_code=201)
def create_user(
    payload: UserCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    existing = db.query(User).filter(func.lower(User.username) == payload.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Tên đăng nhập đã tồn tại.")

    organization_id = None
    if payload.role == "CUSTOMER":
        if payload.organization_id is None:
            raise HTTPException(status_code=422, detail="Tài khoản khách hàng phải được gắn với một tổ chức.")
        organization = db.query(Organization).filter(Organization.id == payload.organization_id).first()
        if not organization:
            raise HTTPException(status_code=422, detail="Không tìm thấy tổ chức đã chọn.")
        organization_id = organization.id

    unit_ids: List[int] = []
    if payload.role == "PORT_STAFF" and payload.reporting_unit_ids:
        unit_ids = sorted(set(payload.reporting_unit_ids))
        found = db.query(ReportingUnit.id).filter(ReportingUnit.id.in_(unit_ids)).all()
        if len(found) != len(unit_ids):
            raise HTTPException(status_code=422, detail="Một hoặc nhiều đơn vị báo cáo không tồn tại.")

    new_user = User(
        username=payload.username,
        password_hash=get_password_hash(payload.password),
        full_name=payload.full_name,
        email=payload.email,
        role=payload.role,
        organization_id=organization_id,
        is_active=1,
        created_at=now_iso(),
    )
    db.add(new_user)
    db.flush()

    for unit_id in unit_ids:
        db.add(ReportingUnitUser(reporting_unit_id=unit_id, user_id=new_user.id, created_at=now_iso()))

    audit(
        db, "USER", new_user.id, "CREATE",
        f"Tạo tài khoản {new_user.username} ({new_user.role})",
        actor_user_id=user.id, organization_id=organization_id,
    )
    db.commit()
    db.refresh(new_user)
    return _serialize_user(db, new_user)


@router.put("/api/admin/users/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    """Admin edits a user's contact fields (email, full name). Username, role and
    password are managed through their own dedicated flows."""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    if payload.full_name is not None:
        target.full_name = payload.full_name
    if payload.email is not None:
        target.email = payload.email
    audit(
        db, "USER", target.id, "PROFILE_ADMIN_UPDATE",
        f"Cập nhật thông tin {target.username}",
        actor_user_id=user.id, organization_id=target.organization_id,
    )
    db.commit()
    db.refresh(target)
    return _serialize_user(db, target)


@router.post("/api/admin/users/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    payload: UserResetPasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    target.password_hash = get_password_hash(payload.password)
    # Thu hồi mọi token của tài khoản này đang sống — Admin thường reset vì
    # nghi ngờ mật khẩu bị lộ hoặc thiết bị bị mất, nên token cũ phải mất hiệu
    # lực ngay, không chờ tới hạn (xem so sánh pwd_ts trong get_current_user).
    target.password_changed_at = now_iso()
    audit(
        db, "USER", target.id, "RESET_PASSWORD",
        f"Đặt lại mật khẩu cho {target.username}",
        actor_user_id=user.id, organization_id=target.organization_id,
    )
    db.commit()
    return {"status": "ok", "detail": "Đã đặt lại mật khẩu."}


@router.post("/api/admin/users/{user_id}/active")
def set_user_active(
    user_id: int,
    payload: UserActiveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    if target.id == user.id and not payload.is_active:
        raise HTTPException(status_code=400, detail="Không thể tự vô hiệu hóa tài khoản của chính mình.")
    target.is_active = 1 if payload.is_active else 0
    audit(
        db, "USER", target.id, "SET_ACTIVE",
        f"{'Kích hoạt' if payload.is_active else 'Vô hiệu hóa'} tài khoản {target.username}",
        actor_user_id=user.id, organization_id=target.organization_id,
    )
    db.commit()
    db.refresh(target)
    return _serialize_user(db, target)


@router.get("/api/admin/operations-summary")
def admin_operations_summary(
    db: Session = Depends(get_db), user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    today = date.today()
    year_start = date(today.year, 1, 1).isoformat()
    declaration_query = db.query(Declaration).filter(Declaration.declaration_date >= year_start)
    declarations = declaration_query.all()
    approved = [item for item in declarations if item.workflow_status == "APPROVED"]
    pending = [item for item in declarations if item.workflow_status.startswith("PENDING_")]
    tons = teu = 0.0
    for item in approved:
        for cargo_item in (json.loads(item.unload_json or "{}"), json.loads(item.load_json or "{}")):
            tons += float(cargo_item.get("tons") or 0)
            teu += float(cargo_item.get("teu") or 0)

    expiring = sum(
        1 for vessel in db.query(Vessel).all()
        if certificate_status(vessel.certificate_expiry_date) in {"EXPIRING", "EXPIRED"}
    )
    backups = list(BACKUP_DIR.glob(BACKUP_GLOB)) if BACKUP_DIR.exists() else []
    latest_backup = max(backups, key=lambda item: item.stat().st_mtime).name if backups else None
    return {
        "period": {"from": year_start, "to": today.isoformat()},
        "operations": {"declarations": len(declarations), "approved": len(approved), "pending": len(pending), "tons": tons, "teu": teu},
        "fleet": {"vessels": db.query(Vessel).count(), "certificateWarnings": expiring},
        "imports": {"jobs": db.query(ImportJob).count(), "rejectedRows": db.query(func.coalesce(func.sum(ImportJob.rejected_count), 0)).scalar()},
        "storage": {"attachments": db.query(Attachment).count(), "backups": len(backups), "latestBackup": latest_backup},
        "security": {"failedLogins": db.query(AuditEvent).filter(AuditEvent.action.like("LOGIN_FAILURE%")).count(), "disabledUsers": db.query(User).filter(User.is_active == 0).count()},
    }


def _backup_record(path: Path) -> dict[str, Any]:
    manifest_path = path.with_suffix(path.suffix + ".manifest.json")
    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            manifest = {}
    created_at = manifest.get("created_at") or datetime.fromtimestamp(
        path.stat().st_mtime, timezone.utc
    ).isoformat()
    return {
        "filename": path.name,
        "createdAt": created_at,
        "sizeBytes": path.stat().st_size,
        "integrityCheck": manifest.get("integrity_check", "unknown"),
        "sha256": manifest.get("sha256", ""),
    }


@router.get("/api/admin/backups")
def list_admin_backups(user: User = Depends(require_roles("PLATFORM_ADMIN"))):
    del user
    if not BACKUP_DIR.exists():
        return []
    return [
        _backup_record(path)
        for path in sorted(
            BACKUP_DIR.glob(BACKUP_GLOB),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
    ]


@router.post("/api/admin/backups")
def create_admin_backup(
    db: Session = Depends(get_db), user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    if engine.url.get_backend_name() != "postgresql" or not engine.url.database:
        raise HTTPException(
            status_code=503,
            detail="Sao lưu trực tiếp chỉ khả dụng với cấu hình PostgreSQL.",
        )
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    destination = BACKUP_DIR / f"cang_vu-{stamp}{BACKUP_SUFFIX}"
    try:
        create_local_backup(SQLALCHEMY_DATABASE_URL, destination)
        removed = prune_local_backups(BACKUP_DIR)
    except Exception as exc:
        access_logger.exception("Local backup failed")
        raise HTTPException(status_code=500, detail="Không thể tạo bản sao lưu cục bộ.") from exc
    audit(
        db, "BACKUP", 0, "CREATE", destination.name,
        actor_user_id=user.id, organization_id=user.organization_id,
    )
    db.commit()
    return {**_backup_record(destination), "pruned": len(removed)}
