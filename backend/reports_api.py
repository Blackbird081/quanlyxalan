"""Báo cáo Phụ lục 1/2/3 và dashboard sản lượng.

Tách khỏi backend/app.py (khối "REPORTS") — chỉ di chuyển, không đổi logic.
Router giữ nguyên đường dẫn cũ nên hợp đồng API không đổi.

LƯU Ý THỨ TỰ ROUTE: `/api/reports/{kind}` là route bắt-tất-cả, phải khai báo
SAU `/api/reports/analytics` và `/api/reports/appendix2/adjustments`, nếu không
nó sẽ nuốt các đường dẫn đó. Thứ tự trong file này chính là thứ tự đăng ký.
"""
from __future__ import annotations

import json
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, field_validator
from sqlalchemy import false as sql_false
from sqlalchemy.orm import Session

from .database import (
    ROOT, audit, get_db, is_demo_data_active, joined_profile_value, now_iso,
)
from .models import (
    Declaration, HistoricalCargoRow, HistoricalPortCall, HistoricalReportImport,
    Organization, ReportAdjustment, ReportingUnit, Vessel,
)
from .tenant import Scope, register_vessel_ids, require_port_scope, resolve_scope
from .xlsx_io import import_match_key, make_report_xlsx, make_xlsx


router = APIRouter(tags=["reports"])


class ReportAdjustmentRequest(BaseModel):
    report_month: str
    metric: str
    delta: float
    reason: str
    organization_id: Optional[int] = None

    @field_validator("report_month")
    @classmethod
    def valid_report_month(cls, value: str) -> str:
        try:
            datetime.strptime(value, "%Y-%m")
        except ValueError as exc:
            raise ValueError("Tháng báo cáo phải có định dạng YYYY-MM.") from exc
        return value

    @field_validator("metric")
    @classmethod
    def valid_metric(cls, value: str) -> str:
        allowed = {"calls", "passenger_calls"}
        if value not in allowed:
            raise ValueError(f"Chỉ tiêu điều chỉnh phải là một trong: {', '.join(sorted(allowed))}.")
        return value

    @field_validator("reason")
    @classmethod
    def required_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 5:
            raise ValueError("Lý do điều chỉnh phải có ít nhất 5 ký tự.")
        return value


ANALYTICS_PERIODS = {"week", "month", "quarter", "year"}
ANALYTICS_SOURCES = {"live", "historical", "combined"}
REPORT_EXPORT_SOURCES = ANALYTICS_SOURCES
ACTIVE_HISTORICAL_STATUSES = ("COMMITTED", "REVIEW")


def _berth_key(value: Any) -> str:
    return import_match_key(str(value or ""))


def _month_shift(value: date, offset: int) -> date:
    month_index = value.year * 12 + value.month - 1 + offset
    return date(month_index // 12, month_index % 12 + 1, 1)


def _analytics_period(period: str, anchor: date) -> dict[str, Any]:
    if period == "week":
        current_start = anchor - timedelta(days=anchor.weekday())
        current_end = current_start + timedelta(days=6)
        previous_start = current_start - timedelta(days=364)
        labels = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
        bucket = lambda value, start: (value - start).days
        title = "Tổng hợp theo tuần"
        trend_title = "Lượt tàu theo ngày"
        compare = "Tuần này so với cùng kỳ năm trước"
    elif period == "month":
        current_start = anchor.replace(day=1)
        current_end = _month_shift(current_start, 1) - timedelta(days=1)
        previous_start = date(current_start.year - 1, current_start.month, 1)
        labels = [f"Tuần {index}" for index in range(1, 6)]
        bucket = lambda value, start: min(4, (value.day - 1) // 7)
        title = "Tổng hợp theo tháng"
        trend_title = "Lượt tàu theo tuần"
        compare = f"Tháng {current_start.month}/{current_start.year} so với cùng kỳ {previous_start.year}"
    elif period == "quarter":
        quarter_month = ((anchor.month - 1) // 3) * 3 + 1
        current_start = date(anchor.year, quarter_month, 1)
        current_end = _month_shift(current_start, 3) - timedelta(days=1)
        previous_start = date(current_start.year - 1, current_start.month, 1)
        labels = [f"T{_month_shift(current_start, index).month}" for index in range(3)]
        bucket = lambda value, start: (value.year - start.year) * 12 + value.month - start.month
        title = "Tổng hợp theo quý"
        trend_title = "Lượt tàu theo tháng"
        compare = f"Quý {(quarter_month - 1) // 3 + 1}/{current_start.year} so với cùng kỳ {previous_start.year}"
    else:
        current_start = date(anchor.year, 1, 1)
        current_end = date(anchor.year, 12, 31)
        previous_start = date(anchor.year - 1, 1, 1)
        labels = [f"T{index}" for index in range(1, 13)]
        bucket = lambda value, start: value.month - 1
        title = "Tổng hợp theo năm"
        trend_title = "Lượt tàu theo tháng"
        compare = f"Năm {anchor.year} so với {anchor.year - 1}"
    if period == "week":
        previous_end = previous_start + timedelta(days=6)
    elif period == "month":
        previous_end = _month_shift(previous_start, 1) - timedelta(days=1)
    elif period == "quarter":
        previous_end = _month_shift(previous_start, 3) - timedelta(days=1)
    else:
        previous_end = date(previous_start.year, 12, 31)
    return {
        "current_start": current_start,
        "current_end": current_end,
        "previous_start": previous_start,
        "previous_end": previous_end,
        "labels": labels,
        "bucket": bucket,
        "title": title,
        "trend_title": trend_title,
        "compare": compare,
    }


def _date_from_value(raw: Any) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None


def _arrival_operating_date(declaration: Declaration) -> date | None:
    for raw in (declaration.actual_arrival_at, declaration.eta):
        value = _date_from_value(raw)
        if value:
            return value
    return None


def _departure_operating_date(declaration: Declaration) -> date | None:
    for raw in (declaration.actual_departure_at, declaration.etd):
        value = _date_from_value(raw)
        if value:
            return value
    return None


def _declaration_operating_date(declaration: Declaration) -> date | None:
    values = (
        (declaration.actual_departure_at, declaration.etd)
        if declaration.movement_type == "DEPARTURE"
        else (declaration.actual_arrival_at, declaration.eta)
    )
    for raw in values:
        if not raw:
            continue
        value = _date_from_value(raw)
        if value:
            return value
    return None


def _declaration_metrics(declaration: Declaration) -> dict[str, float]:
    def numeric(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    tons = 0.0
    teu = 0.0
    for raw in (declaration.unload_json, declaration.load_json):
        try:
            item = json.loads(raw or "{}")
        except (TypeError, json.JSONDecodeError):
            item = {}
        tons += numeric(item.get("tons"))
        teu += numeric(item.get("teu"))
    return {
        "trips": 1.0,
        "tons": tons,
        "teu": teu,
        "pax": numeric(declaration.passenger_count),
    }


def _month_key(value: date) -> str:
    return value.strftime("%Y-%m")


def _months_between(start: date, end: date) -> list[str]:
    value = start.replace(day=1)
    result = []
    while value <= end:
        result.append(_month_key(value))
        value = _month_shift(value, 1)
    return result


def _historical_window(
    db: Session, unit_id: int, start: date, end: date, labels: list[str], bucket,
    berth: str = "",
) -> dict[str, Any]:
    """Aggregate only active, validated TOS facts using ATB as operating time.

    PL.03 reported times are deliberately excluded: the approved business rule
    makes matched TOS ATB/ATD authoritative. Missing TOS coverage remains
    missing and is never converted to a numeric zero.
    """
    window_months = set(_months_between(start, end))
    imports = db.query(HistoricalReportImport).filter(
        HistoricalReportImport.reporting_unit_id == unit_id,
        HistoricalReportImport.status.in_(ACTIVE_HISTORICAL_STATUSES),
    ).all()
    active_ids = {item.id for item in imports}
    berth_imports = [item for item in imports
                      if item.source_kind == "tos_berth_call" and item.reporting_period in window_months]
    cargo_imports = [item for item in imports
                     if item.source_kind == "tos_cargo_detail" and item.reporting_period in window_months]
    berth_months = {item.reporting_period for item in berth_imports}
    cargo_months = {item.reporting_period for item in cargo_imports}
    reported_months = {
        item.reporting_period for item in imports
        if item.source_kind == "reported_pl03" and item.reporting_period in window_months
    }
    if not active_ids:
        return {
            "values": {"trips": None, "tons": None, "teu": None, "pax": None},
            "available": {"trips": False, "tons": False, "teu": False, "pax": False},
            "trend": [0] * len(labels), "months": {}, "coverageMonths": [],
            "reportedMonths": sorted(reported_months), "hasCoverage": bool(reported_months),
            "hasReview": False, "berths": [], "tosCoverageMonths": [],
            "hasTosCoverage": False,
        }

    all_calls = db.query(HistoricalPortCall).filter(
        HistoricalPortCall.reporting_unit_id == unit_id,
        HistoricalPortCall.import_id.in_(active_ids),
        HistoricalPortCall.validation_status == "VALID",
        HistoricalPortCall.actual_berthing_at >= start.isoformat(),
        HistoricalPortCall.actual_berthing_at < (end + timedelta(days=1)).isoformat(),
    ).all()
    berths = sorted({
        str(call.source_berth_raw or call.arrival_berth or "").strip()
        for call in all_calls if str(call.source_berth_raw or call.arrival_berth or "").strip()
    })
    selected_berth = _berth_key(berth)
    calls = [
        call for call in all_calls
        if not selected_berth
        or _berth_key(call.source_berth_raw or call.arrival_berth) == selected_berth
    ]
    call_ids = [item.id for item in calls]
    cargo_rows = []
    if call_ids:
        cargo_rows = db.query(HistoricalCargoRow).filter(
            HistoricalCargoRow.reporting_unit_id == unit_id,
            HistoricalCargoRow.import_id.in_(active_ids),
            HistoricalCargoRow.port_call_id.in_(call_ids),
            HistoricalCargoRow.match_status == "MATCHED",
            HistoricalCargoRow.validation_status == "VALID",
        ).all()

    trend = [0] * len(labels)
    months: dict[str, dict[str, int]] = {}
    for call in calls:
        operating_date = _date_from_value(call.actual_berthing_at)
        if operating_date is None:
            continue
        month = _month_key(operating_date)
        months.setdefault(month, {"calls": 0, "cargoRows": 0})["calls"] += 1
        index = bucket(operating_date, start)
        if 0 <= index < len(trend):
            trend[index] += 1
    call_month_by_id = {call.id: call.reporting_month for call in calls}
    for row in cargo_rows:
        month = call_month_by_id.get(row.port_call_id)
        if month:
            months.setdefault(month, {"calls": 0, "cargoRows": 0})["cargoRows"] += 1
            cargo_months.add(month)

    berth_complete = bool(berth_months) and all(
        item.status == "COMMITTED" and item.review_count == 0 for item in berth_imports
    )
    cargo_complete = bool(berth_months) and berth_months.issubset(cargo_months) and all(
        item.status == "COMMITTED" and item.review_count == 0 for item in cargo_imports
    )
    has_review = any(
        item.status == "REVIEW" or item.review_count > 0 for item in berth_imports + cargo_imports
    )
    return {
        "values": {
            "trips": float(len(calls)) if berth_complete else None,
            "tons": float(sum(row.weight_tonnes or 0 for row in cargo_rows)) if cargo_complete else None,
            "teu": float(sum(row.teu_factor or 0 for row in cargo_rows)) if cargo_complete else None,
            "pax": None,
        },
        "available": {
            "trips": berth_complete, "tons": cargo_complete,
            "teu": cargo_complete, "pax": False,
        },
        "trend": trend if berth_complete else [0] * len(labels), "months": months,
        "coverageMonths": sorted(berth_months | cargo_months | reported_months),
        "tosCoverageMonths": sorted(berth_months | cargo_months),
        "reportedMonths": sorted(reported_months),
        "hasCoverage": bool(berth_months or cargo_months or reported_months),
        "hasTosCoverage": bool(berth_months or cargo_months),
        "hasReview": has_review,
        "berths": berths,
    }


def _analytics_payload(
    db: Session, scope: Scope, period: str, anchor: date, source: str = "live",
    berth: str = "",
) -> dict[str, Any]:
    config = _analytics_period(period, anchor)
    query = db.query(Declaration).filter(Declaration.workflow_status == "APPROVED")
    if scope.is_customer:
        query = query.filter(Declaration.organization_id == scope.organization_id)
    else:
        org_ids = scope.member_org_ids
        query = query.filter(Declaration.organization_id.in_(org_ids)) if org_ids else query.filter(sql_false())
    declarations = query.all()
    live_totals = {
        "cur": {key: 0.0 for key in ("trips", "tons", "teu", "pax")},
        "prev": {key: 0.0 for key in ("trips", "tons", "teu", "pax")},
    }
    live_trend_current = [0] * len(config["labels"])
    live_trend_previous = [0] * len(config["labels"])
    live_months: dict[str, int] = {}
    selected_berth = berth.strip()
    live_berths: set[str] = set()
    for declaration in declarations:
        operating_date = _declaration_operating_date(declaration)
        if not operating_date:
            continue
        operating_berth = str(declaration.working_port or declaration.departure_berth or "").strip()
        if config["current_start"] <= operating_date <= config["current_end"]:
            group = "cur"
            trend = live_trend_current
            start = config["current_start"]
        elif config["previous_start"] <= operating_date <= config["previous_end"]:
            group = "prev"
            trend = live_trend_previous
            start = config["previous_start"]
        else:
            continue
        if operating_berth:
            live_berths.add(operating_berth)
        if selected_berth and _berth_key(operating_berth) != _berth_key(selected_berth):
            continue
        for key, value in _declaration_metrics(declaration).items():
            live_totals[group][key] += value
        month = _month_key(operating_date)
        live_months[month] = live_months.get(month, 0) + 1
        index = config["bucket"](operating_date, start)
        if 0 <= index < len(trend):
            trend[index] += 1
    historical = None
    overlap_months: list[str] = []
    warnings: list[str] = []
    if source in {"historical", "combined"}:
        if not scope.is_port:
            raise HTTPException(
                status_code=403,
                detail="Dữ liệu lịch sử/TOS chỉ dành cho Nhân viên Cảng trong đúng đơn vị báo cáo.",
            )
        historical = {
            "cur": _historical_window(
                db, scope.reporting_unit_id, config["current_start"], config["current_end"],
                config["labels"], config["bucket"], selected_berth,
            ),
            "prev": _historical_window(
                db, scope.reporting_unit_id, config["previous_start"], config["previous_end"],
                config["labels"], config["bucket"], selected_berth,
            ),
        }
        historical_months = (
            set(historical["cur"]["coverageMonths"]) | set(historical["prev"]["coverageMonths"])
        )
        overlap_months = sorted(set(live_months) & historical_months)
        if overlap_months:
            warnings.append(
                "Có kỳ đồng thời chứa dữ liệu LIVE và LỊCH SỬ; tổng KẾT HỢP bị khóa cho đến khi đối soát nguồn."
            )
        if historical["cur"]["reportedMonths"] or historical["prev"]["reportedMonths"]:
            warnings.append(
                "PL.03 cũ chỉ được giữ làm dấu vết báo cáo; thống kê thời gian dùng ATB/ATD từ TOS."
            )
        if historical["cur"]["hasReview"] or historical["prev"]["hasReview"]:
            warnings.append(
                "Một hoặc nhiều lượt import còn dòng cần kiểm tra; chỉ tiêu liên quan không được hiển thị như tổng hoàn chỉnh."
            )

    combined_blocked = source == "combined" and bool(overlap_months)
    kpis: dict[str, dict[str, float | None]] = {}
    if source == "live":
        kpis = {key: {"cur": live_totals["cur"][key], "prev": live_totals["prev"][key]}
                for key in live_totals["cur"]}
        trend_current, trend_previous = live_trend_current, live_trend_previous
    elif source == "historical":
        kpis = {key: {"cur": historical["cur"]["values"][key],
                       "prev": historical["prev"]["values"][key]}
                for key in live_totals["cur"]}
        trend_current, trend_previous = historical["cur"]["trend"], historical["prev"]["trend"]
    elif combined_blocked:
        kpis = {key: {"cur": None, "prev": None} for key in live_totals["cur"]}
        trend_current = trend_previous = [0] * len(config["labels"])
    else:
        for key in live_totals["cur"]:
            values: dict[str, float | None] = {}
            for group in ("cur", "prev"):
                hist_value = historical[group]["values"][key]
                # Never turn absent/incomplete historical coverage into zero.
                # Passenger counts are absent from TOS, and any other metric is
                # withheld while its relevant import still needs review.
                if (historical[group]["hasCoverage"]
                        and not historical[group]["available"][key]):
                    values[group] = None
                else:
                    values[group] = live_totals[group][key] + (hist_value or 0)
            kpis[key] = values
        trend_current = [a + b for a, b in zip(live_trend_current, historical["cur"]["trend"])]
        trend_previous = [a + b for a, b in zip(live_trend_previous, historical["prev"]["trend"])]

    coverage_periods = []
    all_months = _months_between(config["previous_start"], config["previous_end"])
    all_months += [month for month in _months_between(config["current_start"], config["current_end"])
                   if month not in all_months]
    for month in all_months:
        hist_month = None
        if historical:
            hist_month = historical["cur"]["months"].get(month) or historical["prev"]["months"].get(month)
        coverage_periods.append({
            "month": month, "liveApproved": live_months.get(month, 0),
            "historicalCalls": (hist_month or {}).get("calls", 0),
            "historicalCargoRows": (hist_month or {}).get("cargoRows", 0),
            "overlap": month in overlap_months,
        })
    if combined_blocked:
        coverage_status = "BLOCKED"
    elif source == "live":
        coverage_status = "COMPLETE"
    elif historical and all(historical["cur"]["available"][key] for key in ("trips", "tons", "teu")):
        coverage_status = "COMPLETE"
    elif historical and historical["cur"]["hasCoverage"]:
        coverage_status = "PARTIAL"
    else:
        coverage_status = "MISSING"

    historical_berths = set()
    if historical:
        historical_berths.update(historical["cur"].get("berths", []))
        historical_berths.update(historical["prev"].get("berths", []))
    if source == "live":
        available_berths = live_berths
    elif source == "historical":
        available_berths = historical_berths
    else:
        available_berths = live_berths | historical_berths

    return {
        "period": period,
        "asOf": anchor.isoformat(),
        "source": source,
        "dataSource": "DEMO" if source == "live" and is_demo_data_active(db) else source.upper(),
        "combinedAllowed": not combined_blocked,
        "kpis": kpis,
        "trend": {"labels": config["labels"], "cur": trend_current, "prev": trend_previous},
        "coverage": {
            "status": coverage_status, "periods": coverage_periods,
            "overlapPeriods": overlap_months, "warnings": warnings,
        },
        "filters": {"berth": selected_berth, "berths": sorted(available_berths)},
        "meta": {
            "analyticsTitle": config["title"],
            "trendTitle": config["trend_title"],
            "trendSub": f"{config['current_start'].isoformat()} → {config['current_end'].isoformat()}",
            "compareSub": config["compare"],
        },
    }


@router.get("/api/reports/analytics")
def report_analytics(
    period: str = "month",
    source: str = "live",
    berth: str = Query(default="", max_length=100),
    as_of: Optional[date] = None,
    db: Session = Depends(get_db),
    scope: Scope = Depends(resolve_scope),
):
    if period not in ANALYTICS_PERIODS:
        raise HTTPException(status_code=422, detail="Kỳ thống kê phải là week, month, quarter hoặc year.")
    if source not in ANALYTICS_SOURCES:
        raise HTTPException(status_code=422, detail="Nguồn thống kê phải là live, historical hoặc combined.")
    return _analytics_payload(db, scope, period, as_of or date.today(), source, berth)


@router.get("/api/reports/analytics/export")
def export_analytics(
    period: str = "month",
    source: str = "live",
    berth: str = Query(default="", max_length=100),
    as_of: Optional[date] = None,
    db: Session = Depends(get_db),
    scope: Scope = Depends(resolve_scope),
):
    if period not in ANALYTICS_PERIODS:
        raise HTTPException(status_code=422, detail="Kỳ thống kê không hợp lệ.")
    if source not in ANALYTICS_SOURCES:
        raise HTTPException(status_code=422, detail="Nguồn thống kê không hợp lệ.")
    payload = _analytics_payload(db, scope, period, as_of or date.today(), source, berth)
    if not payload["combinedAllowed"]:
        raise HTTPException(status_code=409, detail="Không thể xuất tổng kết hợp khi kỳ dữ liệu còn chồng lấn chưa đối soát.")
    labels = {"trips": "Lượt tàu", "tons": "Khối lượng (tấn)", "teu": "TEU", "pax": "Hành khách"}
    rows = [[labels[key], values["cur"], values["prev"],
             None if values["cur"] is None or values["prev"] is None else values["cur"] - values["prev"]]
            for key, values in payload["kpis"].items()]
    content = make_xlsx(payload["meta"]["analyticsTitle"], ["Chỉ tiêu", "Kỳ này", "Kỳ trước", "Chênh lệch"], rows)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="analytics_{source}_{period}_{payload["asOf"]}.xlsx"'},
    )


def _approved_report_query(db: Session, scope: Scope):
    query = db.query(Declaration).filter(Declaration.workflow_status == "APPROVED")
    if scope.is_customer:
        query = query.filter(Declaration.organization_id == scope.organization_id)
    else:
        org_ids = scope.member_org_ids
        query = query.filter(Declaration.organization_id.in_(org_ids)) if org_ids else query.filter(sql_false())
    return query


def _report_vessel(db: Session, declaration: Declaration) -> Optional[Vessel]:
    if declaration.vessel_id:
        vessel = db.query(Vessel).filter(Vessel.id == declaration.vessel_id).first()
        if vessel:
            return vessel
    return db.query(Vessel).filter(
        Vessel.registration_no == declaration.registration_no
    ).first()


def _report_static_value(vessel: Optional[Vessel], declaration: Optional[Declaration], field: str) -> Any:
    if vessel is not None:
        value = getattr(vessel, field, None)
        if value not in (None, ""):
            return value
    return getattr(declaration, field, None) if declaration is not None else None


def _report_base_vessels(db: Session, scope: Scope) -> list[Vessel]:
    query = db.query(Vessel)
    if scope.is_customer:
        query = query.filter(Vessel.organization_id == scope.organization_id)
    else:
        # The tenant-scoped register (not the legacy global flag) bounds this unit's fleet.
        register_ids = register_vessel_ids(db, scope.reporting_unit_id)
        query = query.filter(Vessel.id.in_(register_ids)) if register_ids else query.filter(sql_false())
    return query.order_by(Vessel.registration_no, Vessel.id).all()


def _report_group_key(vessel_id: Optional[int], registration_no: str) -> str:
    return f"id:{vessel_id}" if vessel_id else f"reg:{import_match_key(registration_no)}"


def _declaration_report_group_key(db: Session, declaration: Declaration) -> str:
    vessel = _report_vessel(db, declaration)
    return _report_group_key(
        vessel.id if vessel else declaration.vessel_id,
        vessel.registration_no if vessel else declaration.registration_no,
    )


def _cargo_summary(item: dict[str, Any]) -> str:
    parts = [str(item.get("cargo_name") or item.get("cargo_type") or "").strip()]
    tons = float(item.get("tons") or 0)
    teu = float(item.get("teu") or 0)
    if tons:
        parts.append(f"{tons:g} tấn")
    if teu:
        parts.append(f"{teu:g} TEU")
    return " - ".join(part for part in parts if part)


def _appendix1_rows(
    db: Session,
    declarations: list[Declaration],
    vessels: Optional[list[Vessel]] = None,
) -> list[list[Any]]:
    groups: dict[str, list[Declaration]] = {}
    for declaration in declarations:
        groups.setdefault(_declaration_report_group_key(db, declaration), []).append(declaration)
    base_vessels = vessels or []
    vessel_by_key = {_report_group_key(vessel.id, vessel.registration_no): vessel for vessel in base_vessels}
    ordered_keys = list(vessel_by_key)
    ordered_keys.extend(key for key in groups if key not in vessel_by_key)

    rows = []
    for index, key in enumerate(ordered_keys, start=1):
        group = groups.get(key, [])
        group.sort(key=lambda item: (_declaration_operating_date(item) or date.max, item.id))
        declaration = group[0] if group else None
        vessel = vessel_by_key.get(key) or (_report_vessel(db, declaration) if declaration else None)
        capacity_tons = joined_profile_value(vessel, "cargo_capacity_tons") if vessel else None
        capacity_teu = getattr(vessel, "container_capacity_teu", None) if vessel else None
        capacity = " / ".join(
            value for value in (
                f"{capacity_tons} tấn" if capacity_tons not in (None, "") else "",
                f"{capacity_teu:g} TEU" if isinstance(capacity_teu, (int, float)) and capacity_teu else "",
            ) if value
        )
        master_name = getattr(vessel, "tracking_master_name", "") if vessel else ""
        master_phone = getattr(vessel, "tracking_master_phone", "") if vessel else ""
        rows.append([
            index,
            _report_static_value(vessel, declaration, "name") or (declaration.vessel_name if declaration else ""),
            _report_static_value(vessel, declaration, "registration_no") or (declaration.registration_no if declaration else ""),
            _report_static_value(vessel, declaration, "vessel_class") or "",
            _report_static_value(vessel, declaration, "vessel_type") or "",
            _report_static_value(vessel, declaration, "certificate_expiry_date") or "",
            capacity,
            getattr(vessel, "passenger_capacity", None) if vessel else None,
            _distinct_join([item.working_port for item in group]),
            _distinct_join([item.actual_arrival_at or item.eta for item in group]),
            _distinct_join([item.departure_berth for item in group]),
            _distinct_join([item.actual_departure_at or item.etd for item in group]),
            _distinct_join([_cargo_summary(json.loads(item.unload_json or "{}")) for item in group]),
            _distinct_join([_cargo_summary(json.loads(item.load_json or "{}")) for item in group]),
            _distinct_join([f"{item.crew_count} / {item.passenger_count}" for item in group]),
            " - ".join(value for value in (
                master_name or (declaration.master_name if declaration else ""),
                master_phone or (declaration.master_phone if declaration else ""),
            ) if value),
        ])
    return rows


def _report_period_metrics(declarations: list[Declaration]) -> dict[str, float | None]:
    metrics = {
        "container_tons": None, "container_teu": None,
        "dry_tons": None, "liquid_tons": None, "foreign_tons": None,
        "calls": None,
        "passenger_calls": None, "passengers": None,
    }

    def add(key: str, value: float, *, applicable: bool = False) -> None:
        if not applicable and not value:
            return
        metrics[key] = float(metrics[key] or 0) + value

    for declaration in declarations:
        if declaration.movement_type == "ARRIVAL":
            add("calls", 1.0, applicable=True)
        add("passengers", float(declaration.passenger_count or 0), applicable=bool(declaration.passenger_count))
        if declaration.movement_type == "ARRIVAL" and declaration.is_passenger_call:
            add("passenger_calls", 1.0, applicable=True)
        for item in (json.loads(declaration.unload_json or "{}"), json.loads(declaration.load_json or "{}")):
            cargo_key = import_match_key(item.get("cargo_type"))
            movement_key = import_match_key(item.get("movement_type"))
            tons = float(item.get("tons") or 0)
            teu = float(item.get("teu") or 0)
            if "CONTAINER" in cargo_key or "CONGTENO" in cargo_key:
                add("container_tons", tons, applicable=bool(tons))
                add("container_teu", teu, applicable=bool(teu))
            elif "HANGKHO" in cargo_key or cargo_key == "KHO":
                add("dry_tons", tons, applicable=bool(tons))
            elif "HANGLONG" in cargo_key or cargo_key == "LONG":
                add("liquid_tons", tons, applicable=bool(tons))
            if "NHAPKHAU" in movement_key or "XUATKHAU" in movement_key:
                add("foreign_tons", tons, applicable=bool(tons))
    return metrics


def _appendix2_rows(
    current: list[Declaration],
    cumulative: list[Declaration],
    current_adjustments: Optional[dict[str, float]] = None,
    cumulative_adjustments: Optional[dict[str, float]] = None,
) -> list[list[Any]]:
    current_metrics = _apply_report_adjustments(
        _report_period_metrics(current), current_adjustments or {},
    )
    cumulative_metrics = _apply_report_adjustments(
        _report_period_metrics(cumulative), cumulative_adjustments or {},
    )
    return _appendix2_metric_rows(current_metrics, cumulative_metrics)


def _apply_report_adjustments(
    metrics: dict[str, float | None], adjustments: dict[str, float],
) -> dict[str, float | None]:
    result = dict(metrics)
    for key, delta in adjustments.items():
        if key in result and delta:
            result[key] = float(result[key] or 0) + float(delta)
    return result


def _appendix2_metric_rows(
    current_metrics: dict[str, float | None],
    cumulative_metrics: dict[str, float | None],
) -> list[list[Any]]:
    values = [
        current_metrics["container_tons"], current_metrics["container_teu"],
        cumulative_metrics["container_tons"], cumulative_metrics["container_teu"],
        current_metrics["dry_tons"], cumulative_metrics["dry_tons"],
        current_metrics["liquid_tons"], cumulative_metrics["liquid_tons"],
        current_metrics["foreign_tons"], cumulative_metrics["foreign_tons"],
        current_metrics["calls"], cumulative_metrics["calls"],
        current_metrics["passenger_calls"], current_metrics["passengers"],
    ]
    return [
        ["I", "Bến cảng biển", *([None] * 14)],
        [None, "- Cảng Tân Thuận", *values],
        ["Tổng", None, *values],
    ]


def _historical_appendix2_metrics(window: dict[str, Any]) -> dict[str, float | None]:
    available = window["available"]
    values = window["values"]
    return {
        "container_tons": values["tons"] if available["tons"] else None,
        "container_teu": values["teu"] if available["teu"] else None,
        "dry_tons": None,
        "liquid_tons": None,
        "foreign_tons": None,
        "calls": values["trips"] if available["trips"] else None,
        "passenger_calls": None,
        "passengers": None,
    }


def _combined_appendix2_metrics(
    live: dict[str, float | None],
    historical: dict[str, float | None],
    *, has_historical_coverage: bool,
) -> dict[str, float | None]:
    if not has_historical_coverage:
        return dict(live)
    combined: dict[str, float | None] = {}
    for key, historical_value in historical.items():
        if historical_value is None:
            # The requested historical window contains no trustworthy source
            # for this metric. Preserve "unknown" instead of under-reporting.
            combined[key] = None
        else:
            combined[key] = float(live.get(key) or 0) + float(historical_value)
    return combined


def _historical_report_window(
    db: Session, unit_id: int, start: date, end: date,
) -> dict[str, Any]:
    return _historical_window(
        db, unit_id, start, end, ["Kỳ"], lambda _value, _start: 0,
    )


def _live_months(
    declarations: list[Declaration], start: date, end: date, *, arrival_only: bool,
) -> set[str]:
    extractor = _arrival_operating_date if arrival_only else _declaration_operating_date
    return {
        _month_key(value)
        for declaration in declarations
        if (value := extractor(declaration)) and start <= value <= end
    }


def _historical_pl03_export_rows(
    db: Session, unit_id: int, start: date, end: date, *, required: bool = True,
) -> tuple[list[list[Any]], set[str]]:
    from .historical_api import _historical_pl03_rows

    periods = [
        value for value, in db.query(HistoricalPortCall.reporting_month)
        .join(
            HistoricalReportImport,
            HistoricalReportImport.id == HistoricalPortCall.import_id,
        )
        .filter(
            HistoricalPortCall.reporting_unit_id == unit_id,
            HistoricalPortCall.validation_status != "REJECTED",
            HistoricalPortCall.actual_berthing_at >= start.isoformat(),
            HistoricalPortCall.actual_berthing_at < (end + timedelta(days=1)).isoformat(),
            HistoricalReportImport.source_kind == "tos_berth_call",
            HistoricalReportImport.status.in_(ACTIVE_HISTORICAL_STATUSES),
        ).distinct().order_by(HistoricalPortCall.reporting_month).all()
        if value
    ]
    if not periods:
        if not required:
            return [], set()
        raise HTTPException(
            status_code=409,
            detail="Kỳ đã chọn chưa có dữ liệu Berth lịch sử/TOS đã xác nhận để xuất PL.03.",
        )
    rows: list[list[Any]] = []
    for period in periods:
        try:
            period_rows, _receipt = _historical_pl03_rows(
                db, unit_id, period, report_start=start, report_end=end,
            )
        except HTTPException as exc:
            if exc.status_code == 409:
                raise HTTPException(
                    status_code=409,
                    detail=f"Kỳ {period}: {exc.detail}",
                ) from exc
            raise
        rows.extend(period_rows)
    for index, row in enumerate(rows, start=1):
        row[0] = index
    return rows, set(periods)


def _pl03_row_time_key(row: list[Any]) -> tuple[datetime, str, int]:
    raw = str(row[32] or "").splitlines()[0].strip()
    parsed = None
    if raw:
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            for pattern in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
                try:
                    parsed = datetime.strptime(raw, pattern)
                    break
                except ValueError:
                    continue
    return parsed or datetime.max, str(row[1] or ""), int(row[0] or 0)


def _cargo_column_start(movement_type: str, cargo_direction: str = "") -> int:
    key = import_match_key(movement_type)
    if "XUATKHAU" in key:
        return 8
    if "NHAPKHAU" in key:
        return 11
    if "NOIDIADEN" in key:
        return 14
    if "NOIDIAROI" in key:
        return 17
    if "NOIDIA" in key:
        if cargo_direction == "unload":
            return 14
        if cargo_direction == "load":
            return 17
    if "CHUYENTAI" in key:
        return 20
    if "QUACANH" in key and ("BOCDO" in key or "XEPDO" in key):
        return 22
    if "QUACANH" in key or "QUACANG" in key:
        return 24
    raise ValueError(f"Không nhận diện được nhóm hàng hóa '{movement_type or '(trống)'}'.")


def _distinct_join(values: list[Any]) -> str:
    result: list[str] = []
    for value in values:
        text_value = str(value or "").strip()
        if text_value and text_value not in result:
            result.append(text_value)
    return "\n".join(result)


def _appendix3_rows(
    db: Session,
    declarations: list[Declaration],
    vessels: Optional[list[Vessel]] = None,
) -> list[list[Any]]:
    rows: list[list[Any]] = []
    groups: dict[str, list[Declaration]] = {}
    for declaration in declarations:
        key = _declaration_report_group_key(db, declaration)
        groups.setdefault(key, []).append(declaration)

    base_vessels = vessels or []
    vessel_by_key = {_report_group_key(vessel.id, vessel.registration_no): vessel for vessel in base_vessels}
    ordered_keys = list(vessel_by_key)
    unmatched_keys = [key for key in groups if key not in vessel_by_key]
    unmatched_keys.sort(key=lambda key: (_declaration_operating_date(groups[key][0]) or date.max, groups[key][0].id))
    ordered_keys.extend(unmatched_keys)
    for key in ordered_keys:
        group = groups.get(key, [])
        group.sort(key=lambda item: (_declaration_operating_date(item) or date.max, item.id))
        declaration = group[0] if group else None
        vessel = vessel_by_key.get(key) or (_report_vessel(db, declaration) if declaration else None)
        row: list[Any] = [None] * 35
        row[0] = len(rows) + 1
        row[1] = _report_static_value(vessel, declaration, "name") or (declaration.vessel_name if declaration else "")
        row[2] = _report_static_value(vessel, declaration, "registration_no") or (declaration.registration_no if declaration else "")
        row[3] = _report_static_value(vessel, declaration, "vessel_type") or ""
        row[4] = _report_static_value(vessel, declaration, "vessel_class") or ""
        row[5] = _report_static_value(vessel, declaration, "length_m")
        row[6] = joined_profile_value(vessel, "deadweight_tons") if vessel else (declaration.deadweight_tons if declaration else None)
        row[7] = _report_static_value(vessel, declaration, "gross_tonnage")
        cargo_names: list[str] = []
        for item_declaration in group:
            for cargo_direction, item in (
                ("unload", json.loads(item_declaration.unload_json or "{}")),
                ("load", json.loads(item_declaration.load_json or "{}")),
            ):
                if not any((item.get("cargo_type"), item.get("cargo_name"), item.get("tons"), item.get("teu"), item.get("empty_teu"))):
                    continue
                cargo_start = _cargo_column_start(str(item.get("movement_type") or ""), cargo_direction)
                for offset, item_key in ((0, "tons"), (1, "teu")):
                    value = float(item.get(item_key) or 0)
                    if value:
                        row[cargo_start + offset] = float(row[cargo_start + offset] or 0) + value
                if cargo_start in {8, 11, 14, 17}:
                    empty_teu = float(item.get("empty_teu") or 0)
                    if empty_teu:
                        row[cargo_start + 2] = float(row[cargo_start + 2] or 0) + empty_teu
                cargo_names.append(str(item.get("cargo_name") or item.get("cargo_type") or ""))
        for item_declaration in group:
            if item_declaration.passenger_count:
                column = 26 if item_declaration.movement_type == "ARRIVAL" else 27
                row[column] = int(row[column] or 0) + int(item_declaration.passenger_count)
        row[28] = _distinct_join(cargo_names)
        row[29] = _distinct_join([item.last_port for item in group])
        row[30] = _distinct_join([item.working_port for item in group])
        row[31] = _distinct_join([item.destination_port for item in group])
        row[32] = _distinct_join([item.actual_arrival_at or item.eta for item in group])
        row[33] = _distinct_join([item.actual_departure_at or item.etd for item in group])
        row[34] = _distinct_join([item.agent_ptnd_name for item in group])
        rows.append(row)
    return rows


def _report_adjustment_totals(
    db: Session,
    start_month: str,
    end_month: str,
    scope: Scope,
) -> dict[str, float]:
    query = db.query(ReportAdjustment).filter(
        ReportAdjustment.report_kind == "appendix2",
        ReportAdjustment.report_month >= start_month,
        ReportAdjustment.report_month <= end_month,
    )
    if scope.is_customer:
        query = query.filter(ReportAdjustment.organization_id == scope.organization_id)
    else:
        query = query.filter(ReportAdjustment.reporting_unit_id == scope.reporting_unit_id)
    totals: dict[str, float] = {}
    for adjustment in query.all():
        totals[adjustment.metric] = totals.get(adjustment.metric, 0.0) + adjustment.delta
    return totals


@router.get("/api/reports/appendix2/adjustments")
def list_appendix2_adjustments(
    report_month: Optional[str] = None,
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    query = db.query(ReportAdjustment).filter(
        ReportAdjustment.report_kind == "appendix2",
        ReportAdjustment.reporting_unit_id == scope.reporting_unit_id,
    )
    if report_month:
        try:
            datetime.strptime(report_month, "%Y-%m")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Tháng báo cáo phải có định dạng YYYY-MM.") from exc
        query = query.filter(ReportAdjustment.report_month == report_month)
    return [
        {column.name: getattr(item, column.name) for column in item.__table__.columns}
        for item in query.order_by(ReportAdjustment.created_at.desc(), ReportAdjustment.id.desc()).all()
    ]


@router.post("/api/reports/appendix2/adjustments")
def create_appendix2_adjustment(
    payload: ReportAdjustmentRequest,
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    user = scope.user
    if payload.organization_id is not None:
        organization = db.query(Organization).filter(Organization.id == payload.organization_id).first()
        if not organization:
            raise HTTPException(status_code=404, detail="Không tìm thấy đơn vị cần điều chỉnh.")
        scope.require_org(payload.organization_id)
    adjustment = ReportAdjustment(
        report_kind="appendix2",
        report_month=payload.report_month,
        metric=payload.metric,
        delta=payload.delta,
        reason=payload.reason,
        organization_id=payload.organization_id,
        reporting_unit_id=scope.reporting_unit_id,
        actor_user_id=user.id,
        created_at=now_iso(),
    )
    db.add(adjustment)
    db.flush()
    audit(
        db, "REPORT_ADJUSTMENT", adjustment.id, "CREATE",
        f"PL.02 {payload.report_month} {payload.metric} {payload.delta:+g}: {payload.reason}",
        actor_user_id=user.id, organization_id=payload.organization_id,
        reporting_unit_id=scope.reporting_unit_id,
    )
    db.commit()
    db.refresh(adjustment)
    return {column.name: getattr(adjustment, column.name) for column in adjustment.__table__.columns}

@router.get("/api/reports/{kind}")
def export_report(
    kind: str,
    from_: Optional[str] = Query(default=None, alias="from"),
    to: Optional[str] = None,
    source: str = Query(default="live"),
    db: Session = Depends(get_db),
    scope: Scope = Depends(resolve_scope),
):
    user = scope.user
    if kind not in ("appendix1", "appendix2", "appendix3"):
        raise HTTPException(status_code=404, detail=f"Loại báo cáo '{kind}' không tồn tại.")
    if source not in REPORT_EXPORT_SOURCES:
        raise HTTPException(
            status_code=422,
            detail="Nguồn xuất báo cáo phải là live, historical hoặc combined.",
        )
    if kind == "appendix1" and source != "live":
        raise HTTPException(
            status_code=422,
            detail="PL.01 chỉ hỗ trợ nguồn LIVE vì dữ liệu TOS không đủ trường kế hoạch.",
        )
    if source != "live" and not scope.is_port:
        raise HTTPException(
            status_code=403,
            detail="Nguồn lịch sử/TOS chỉ dành cho người dùng Cảng trong đúng đơn vị báo cáo.",
        )

    if to:
        try:
            report_end = date.fromisoformat(to)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Ngày kết thúc báo cáo không hợp lệ.") from exc
    else:
        report_end = date.today()
        to = report_end.isoformat()
    if from_:
        try:
            report_start = date.fromisoformat(from_)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Ngày bắt đầu báo cáo không hợp lệ.") from exc
    else:
        report_start = date(report_end.year, 1, 1)
        from_ = report_start.isoformat()
    if report_start > report_end:
        raise HTTPException(status_code=422, detail="Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.")

    query = _approved_report_query(db, scope)
    approved = query.order_by(Declaration.id).all()

    if kind == "appendix2":
        report_start = date(report_end.year, report_end.month, 1)
        report_end = date(report_end.year, report_end.month, monthrange(report_end.year, report_end.month)[1])
        from_ = report_start.isoformat()
        to = report_end.isoformat()
        decls = [item for item in approved if (value := _arrival_operating_date(item)) and report_start <= value <= report_end]
    else:
        decls = [item for item in approved if (value := _declaration_operating_date(item)) and report_start <= value <= report_end]
    decls.sort(key=lambda item: (_declaration_operating_date(item) or date.max, item.id))
    base_vessels = _report_base_vessels(db, scope) if kind in {"appendix1", "appendix3"} else []

    if kind == "appendix1":
        rows = _appendix1_rows(db, decls, base_vessels)

    elif kind == "appendix2":
        cumulative_start = date(report_end.year, 1, 1)
        cumulative = [
            item for item in approved
            if (value := _arrival_operating_date(item)) and cumulative_start <= value <= report_end
        ]
        month_key = report_end.strftime("%Y-%m")
        current_adjustments = _report_adjustment_totals(db, month_key, month_key, scope)
        cumulative_adjustments = _report_adjustment_totals(
            db, f"{report_end.year}-01", month_key, scope,
        )
        if source == "live":
            rows = _appendix2_rows(
                decls, cumulative, current_adjustments, cumulative_adjustments,
            )
        else:
            current_window = _historical_report_window(
                db, scope.reporting_unit_id, report_start, report_end,
            )
            cumulative_window = _historical_report_window(
                db, scope.reporting_unit_id, cumulative_start, report_end,
            )
            historical_current = _historical_appendix2_metrics(current_window)
            historical_cumulative = _historical_appendix2_metrics(cumulative_window)
            if source == "historical":
                if not cumulative_window["hasTosCoverage"]:
                    raise HTTPException(
                        status_code=409,
                        detail="Năm báo cáo chưa có dữ liệu Berth/chi tiết TOS đã xác nhận để xuất PL.02.",
                    )
                rows = _appendix2_metric_rows(
                    historical_current, historical_cumulative,
                )
            else:
                live_coverage = _live_months(
                    cumulative, cumulative_start, report_end, arrival_only=True,
                )
                overlap = sorted(
                    live_coverage & set(cumulative_window["tosCoverageMonths"]),
                )
                if overlap:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Không thể xuất PL.02 KẾT HỢP vì tháng "
                            f"{', '.join(overlap)} có cả LIVE và TOS. Hãy chọn một nguồn để tránh cộng trùng."
                        ),
                    )
                live_current = _apply_report_adjustments(
                    _report_period_metrics(decls), current_adjustments,
                )
                live_cumulative = _apply_report_adjustments(
                    _report_period_metrics(cumulative), cumulative_adjustments,
                )
                rows = _appendix2_metric_rows(
                    _combined_appendix2_metrics(
                        live_current, historical_current,
                        has_historical_coverage=current_window["hasTosCoverage"],
                    ),
                    _combined_appendix2_metrics(
                        live_cumulative, historical_cumulative,
                        has_historical_coverage=cumulative_window["hasTosCoverage"],
                    ),
                )

    else:  # appendix3
        if source == "live":
            try:
                rows = _appendix3_rows(db, decls, base_vessels)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        else:
            historical_rows, historical_months = _historical_pl03_export_rows(
                db, scope.reporting_unit_id, report_start, report_end,
                required=source == "historical",
            )
            if source == "historical":
                rows = historical_rows
            else:
                overlap = sorted(
                    _live_months(decls, report_start, report_end, arrival_only=False)
                    & historical_months,
                )
                if overlap:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Không thể xuất PL.03 KẾT HỢP vì tháng "
                            f"{', '.join(overlap)} có cả LIVE và TOS. Hãy chọn một nguồn để tránh trùng chuyến."
                        ),
                    )
                try:
                    live_rows = _appendix3_rows(db, decls, []) if decls else []
                except ValueError as exc:
                    raise HTTPException(status_code=422, detail=str(exc)) from exc
                rows = sorted(historical_rows + live_rows, key=_pl03_row_time_key)
                for index, row in enumerate(rows, start=1):
                    row[0] = index

    if scope.is_customer:
        reporting_unit_label = user.organization.name if user.organization else "CÔNG TY CỔ PHẦN CẢNG TÂN THUẬN"
    else:
        unit = db.get(ReportingUnit, scope.reporting_unit_id)
        reporting_unit_label = unit.name if unit else "CÔNG TY CỔ PHẦN CẢNG TÂN THUẬN"
    xlsx_bytes = make_report_xlsx(
        kind,
        rows,
        appendix3_template=ROOT / "templates" / "Phụ lục 3.xlsx",
        report_from=report_start,
        report_to=report_end,
        reporting_unit=reporting_unit_label,
    )
    source_suffix = "" if source == "live" else f"_{source}"
    filename = f"report_{kind}{source_suffix}_{from_ or 'all'}_{to or 'all'}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
