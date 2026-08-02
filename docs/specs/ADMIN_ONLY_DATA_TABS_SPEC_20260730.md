# Admin-only Data Tabs Specification

Spec ID: SPEC-QLXL-ADMIN-ONLY-DATA-TABS-20260730

Status: AUTHORIZED_SCOPE

Phase: SPEC

Risk: R2

## Functional Requirements

1. Only `PLATFORM_ADMIN` may see the `Import dữ liệu` navigation item.
2. Only `PLATFORM_ADMIN` may see the `Báo cáo hoạt động` navigation item.
3. `PORT_STAFF` opening `#import` or `#reports` is redirected to
   `#dashboard`.
4. `CUSTOMER` opening `#import` or `#reports` is redirected to
   `#declarations`.
5. Platform Admin retains access to both routes and their existing loaders.
6. Historical import UI copy uses `Bản sửa đổi` instead of the English word
   `Revision`, including headings, table labels, statuses, actions, guidance,
   and revision-number badges.

## Compatibility Requirements

- Preserve existing user-owned edits already present in `frontend/app.js` and
  `frontend/index.html`.
- Do not rename internal `revisionNo`, `ACTIVATE_NEW_REVISION`, DOM ids, CSS
  classes, or backend contracts.
- Do not change backend report/import authorization in this tranche.

## Validation

- Focused frontend UX/static contract tests.
- Existing backend index/static asset contract test.
- JavaScript syntax check.
- `git diff --check`.
- Governed catalog and workspace doctor checks before closure.

## Non-Goals

No backend authorization redesign, production data change, migration,
deployment, merge, or unrelated copy edit.
