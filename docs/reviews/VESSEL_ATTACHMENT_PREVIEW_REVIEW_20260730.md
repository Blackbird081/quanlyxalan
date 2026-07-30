# Vessel Attachment Preview Review

Review ID: REVIEW-QLXL-VESSEL-ATTACHMENT-PREVIEW-20260730

Work order: WO-QLXL-VESSEL-ATTACHMENT-PREVIEW-20260730

Disposition: PASS_WITH_LIMITATIONS

Risk: R2

## Scope Review

- Selecting an attachment filename opens a preview dialog instead of invoking
  browser download.
- PNG, JPEG, WebP, and PDF bytes are fetched through the existing
  authenticated, vessel-scoped endpoint.
- Raster images render as images and PDF renders in a sandboxed iframe.
- Word and Excel show an unsupported-preview message without fetching bytes.
- `Tải xuống` is a separate explicit action and reuses already fetched preview
  bytes when available.
- Object URLs are revoked when the dialog closes or another preview replaces
  the current one; stale asynchronous responses cannot replace a newer popup.
- Existing backend tenant checks and forced-download security headers remain
  unchanged.
- Frontend asset cache keys are synchronized at `1.13.7`.

## Executable Evidence

- `python -m pytest -q tests/test_frontend_ux.py`: 18 passed.
- `tests/test_backend.py::test_vessel_attachment_upload_list_tenant_guard_and_delete`
  against a temporary PostgreSQL 17 service: 1 passed.
- Full suite against temporary PostgreSQL 17: 272 passed, 2 failed because
  local `pg_dump` is not installed in `PATH`; both failures are backup-tool
  environment failures outside this changed set.
- `node --check frontend/app.js`: passed.
- `git diff --check`: passed.

## Findings

No HIGH, MEDIUM, or LOW finding remains in the authorized changed set.

## Limitations

- Browser discovery returned no available session, so no rendered popup
  screenshot or live interaction evidence was captured.
- Office formats intentionally require explicit download; no Office-to-HTML
  conversion is implemented.
- This review does not claim production deployment.

## Claim Boundary

This review covers local attachment UI and application security behavior only.
It makes no live AI-governance claim and therefore does not require provider
API evidence.
