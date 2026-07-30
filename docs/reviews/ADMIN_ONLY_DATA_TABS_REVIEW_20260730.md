# Admin-only Data Tabs Review

Review ID: REVIEW-QLXL-ADMIN-ONLY-DATA-TABS-20260730

Work order: WO-QLXL-ADMIN-ONLY-DATA-TABS-20260730

Disposition: PASS_WITH_LIMITATIONS

Risk: R2

## Scope Review

- `Import dữ liệu` and `Báo cáo hoạt động` are hidden in the initial HTML and
  unhidden only when `isAdmin` is true.
- Non-admin direct routes to `#import` or `#reports` are replaced before any
  restricted page loader runs.
- Port Staff returns to `#dashboard`; Customer returns to `#declarations`.
- Platform Admin route and loader behavior remains unchanged.
- User-visible historical import copy now uses `Bản sửa đổi`; internal
  revision contracts remain unchanged.
- Frontend asset cache keys are synchronized at `1.13.6`.
- Pre-existing ETB, password, and audit-log copy edits remain intact.

## Executable Evidence

- `python -m pytest -q tests/test_frontend_ux.py`: 18 passed.
- `tests/test_backend.py::test_static_frontend` against a temporary PostgreSQL
  17 Docker service: 1 passed.
- `node --check frontend/app.js`: passed.
- `git diff --check`: passed.
- `scripts/manage_cvf_downstream_catalog.ps1 -Check`: passed.
- CVF workspace doctor: 25/25 passed.

## Findings

No HIGH, MEDIUM, or LOW finding remains.

## Limitations

No connected production session or rendered multi-role browser session was
used. The review proves the source/static route contract and local test
behavior; it does not claim production deployment.

## Documentation Follow-up

- `USER_GUIDE.md` now states that LIVE PL.03 from approved declarations and
  historical PL.03 reconstructed from confirmed TOS sources are separate
  workflows sharing the same Excel template.
- The guide records that both Import and Reports menus are Platform Admin-only.
- Operator-authored copy cleanup in the scoped frontend files was preserved.
- Focused frontend UX tests were rerun after the documentation/test alignment:
  18 passed; JavaScript syntax and diff checks passed.

## Claim Boundary

This review covers local application UI/RBAC behavior only. It does not claim
live AI-governance behavior and therefore does not require provider API
evidence.
