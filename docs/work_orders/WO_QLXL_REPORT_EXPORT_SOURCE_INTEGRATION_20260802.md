# Work Order — Report Export Source Integration

Work Order ID: WO-QLXL-REPORT-EXPORT-SOURCE-INTEGRATION-20260802

Status: AUTHORIZED

Risk: R2

## Objective

Expose historical/TOS and safe combined sources in the Activity Report PL.02
and PL.03 exports while keeping PL.01 explicitly LIVE and keeping the UI
compact and unambiguous.

## Authorized Changed Set

- `backend/reports_api.py`
- `backend/historical_api.py` only for reusable date-bounded PL.03 assembly
- `frontend/index.html`
- `frontend/app.js`
- `frontend/styles.css`
- `tests/test_backend.py`
- `tests/test_frontend_ux.py`
- governed design/spec/work-order/review, continuity and catalog truth files

## Required Evidence

1. Focused PostgreSQL API/XLSX tests for LIVE, historical and combined exports.
2. Frontend source/UX tests.
3. Full regression excluding only documented host-tool limitations.
4. Compile, JavaScript syntax, unbound-name, diff, catalog and doctor checks.

## Stop Conditions

- Historical data would be silently represented as zero.
- LIVE and historical overlap cannot be detected reliably.
- Tenant scope cannot be preserved.
- PL.01 would appear to be reconstructed from sources that lack its required
  business fields.

## Authority Boundary

No production data mutation, commit, push, merge, deployment or FREEZE is
authorized.
