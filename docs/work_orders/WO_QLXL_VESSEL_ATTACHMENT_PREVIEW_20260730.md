# Work Order: Vessel Attachment Preview

Work order: WO-QLXL-VESSEL-ATTACHMENT-PREVIEW-20260730

Status: REVIEWED_AWAITING_OPERATOR

Risk: R2

## Authority

The operator requested an attachment preview popup so selecting a filename no
longer downloads immediately and download happens only on explicit request.

## Authorized Changed Set

- `frontend/app.js`
- `frontend/index.html`
- `frontend/styles.css`
- focused tests under `tests/test_frontend_ux.py` and, only if required,
  `tests/test_backend.py`
- this tranche's decision, specification, work order, review, implementation
  truth, and active continuity files

## Acceptance

1. Filename click opens the dialog without automatic download.
2. Raster image and PDF previews render through authenticated bytes.
3. Office formats receive a clear non-preview message and download action.
4. Download requires an explicit click.
5. Object URLs are revoked and errors fail closed.
6. Tenant and quarantine security contracts remain unchanged.
7. Cache keys and focused evidence pass.

## Roles And Sequence

- ORCHESTRATOR completes INTAKE and risk classification.
- SPEC_AUTHOR completes DESIGN and SPEC.
- WORK_ORDER_AUTHOR authorizes this bounded changed set.
- IMPLEMENTATION_WORKER may enter BUILD.
- REVIEWER must compare the security matrix, source, tests, and rendered
  behavior before any publication request.

## Stop Conditions

Stop on a public file URL, storage-key exposure, automatic download, inline
rendering of Office/SVG/HTML content, tenant regression, or need to weaken
backend security headers. Commit, push, merge, deployment, and FREEZE are not
authorized.
