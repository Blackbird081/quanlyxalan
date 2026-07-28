# App Route Extraction Design

Decision ID: ADR-QLXL-APP-SPLIT-20260727

Status: APPROVED_BY_OPERATOR_SCOPE

Phase: DESIGN

Risk: R1

## Intent

Finish the two remaining route extractions documented in `CATALOG.md`:
VESSELS and USER MANAGEMENT.

## Boundaries

- Add `backend/vessels_api.py` with an `APIRouter` owning reporting-unit,
  port-vessel-register, and vessel routes.
- Add `backend/user_management_api.py` with an `APIRouter` owning platform-admin
  user, operations-summary, and local-backup routes.
- Move request models that are used only by those routes into their owning
  modules.
- Move only genuinely shared, app-independent helpers to `backend/shared.py`.
- Import both routers beside the existing router imports, but include each at
  its original route-block position before the static mount so global route
  order remains unchanged.
- Do not change route methods, paths, endpoint names, response shapes, role
  dependencies, transaction behavior, or route order.

## Reverse-Dependency Decision

The visual USER MANAGEMENT section also contains `_attention_queue`,
`_resolve_unit_id_for_reference`, and `_next_reference_no`. AST inspection
shows they are consumed later by dashboard/declaration code. They are not user
management route ownership and will remain in `backend/app.py`.

VESSELS has no reverse dependency from later `app.py` code.

## Shared Dependency Decision

`certificate_status` and `_clean_email` are app-independent helpers needed by
more than one router/module, so they may move to `backend/shared.py`. New router
modules must not import from `backend.app`.

All routers will use the canonical `backend.database.get_db` dependency.
`backend.app.get_db` will remain import-compatible by importing that same
function, preserving existing test overrides.

## Verification

1. Capture ordered baseline tuples of HTTP methods, path, and endpoint name.
2. Static-check each new module with `scripts/check_unbound_names.py`.
3. Import each module independently.
4. Compare the ordered post-change route tuples with the 77-route baseline.
5. Run targeted route tests, then the full test suite.

## Claim Boundary

This design covers application refactoring only. It makes no claim about CVF
governance behavior and therefore does not substitute mock output for live
governance evidence.
