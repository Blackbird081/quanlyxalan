# Admin-only Data Tabs Design

Decision ID: ADR-QLXL-ADMIN-ONLY-DATA-TABS-20260730

Status: APPROVED_BY_OPERATOR_SCOPE

Phase: DESIGN

Risk: R2

## Intent

Limit the `Import dữ liệu` and `Báo cáo hoạt động` application tabs to
Platform Admin accounts and use consistent Vietnamese terminology for
user-visible historical import revisions.

## Access Decision

- `PLATFORM_ADMIN` sees and may route to `#import` and `#reports`.
- `PORT_STAFF` and `CUSTOMER` do not see either navigation item.
- A non-admin opening either hash directly is redirected to an allowed landing
  page: `#dashboard` for Port Staff and `#declarations` for Customer.
- The existing backend authorization contracts are unchanged. This tranche
  controls the requested application tabs and direct frontend routes; it does
  not redefine API consumers or report/import business permissions.

## Terminology Decision

Translate every user-visible instance of `Revision` in the historical import
workspace as `Bản sửa đổi`. Internal API values, field names, element ids, CSS
classes, and implementation comments remain unchanged to avoid an unrelated
contract refactor.

## Alternatives

Backend-wide revocation for report/import APIs was not selected because the
operator asked to hide two application tabs, while those APIs may support
separate established workflows. Expanding that boundary requires a separate
authorization and compatibility review.

## Verification

Focused frontend contract tests must prove role visibility, direct-route
redirection, and removal of the English word from user-visible HTML/JavaScript
strings. JavaScript syntax and diff checks must also pass.

## Claim Boundary

This is application RBAC/UI behavior. It does not claim that CVF controls an AI
provider and does not use mock provider output as governance evidence.
