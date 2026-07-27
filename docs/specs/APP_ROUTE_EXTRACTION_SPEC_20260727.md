# App Route Extraction Specification

Spec ID: SPEC-QLXL-APP-SPLIT-20260727

Status: AUTHORIZED_SCOPE

Phase: SPEC

## Functional Requirements

### FR-1 Route identity

After both extractions, the ordered list of `/api` routes must contain exactly
77 entries and must equal the pre-change baseline for:

- sorted HTTP methods;
- route path;
- endpoint name.

### FR-2 Vessel ownership

`backend/vessels_api.py` must own these route groups without behavioral change:

- `/api/reporting-units`;
- `/api/reporting-unit/organizations`;
- `/api/vessels`;
- `/api/port-vessel-register`.

### FR-3 User-management ownership

`backend/user_management_api.py` must own:

- `/api/admin/users`;
- `/api/admin/operations-summary`;
- `/api/admin/backups`.

The dashboard/declaration helpers discovered inside the old visual section must
remain available to their existing consumers in `backend/app.py`.

### FR-4 Dependency direction

Neither new router module may import `backend.app`. Shared dependencies must
come from lower-level modules such as `database.py`, `shared.py`, `models.py`,
`tenant.py`, or dedicated integration/operations modules.

### FR-5 Registration order

Both routers must be imported with the existing router imports and included at
their original route-block positions before
`app.mount("/", StaticFiles(...))`, preserving global route order.

## Validation Requirements

- `python scripts/check_unbound_names.py backend/vessels_api.py
  backend/user_management_api.py` exits 0.
- `python -c "import backend.vessels_api; import backend.user_management_api"`
  exits 0.
- The ordered route comparison passes exactly.
- Targeted user/vessel/port-register tests pass.
- The full test suite is run. Known environmental `pg_dump` failures must be
  reported rather than silently reclassified as passing.

## Non-Goals

- No endpoint redesign.
- No database schema changes.
- No authorization policy changes.
- No frontend behavior changes.
- No CI integration for the static checker.
- No new CVF skill or second skill system.

## Stop Conditions

Stop BUILD and return to design if:

- a moved symbol requires importing from `backend.app`;
- route count/order/name changes;
- tests expose a behavioral change rather than an environmental failure;
- the changed set crosses into production configuration, secrets, or external
  provider calls.
