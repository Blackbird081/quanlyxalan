# Work Order: Finish App Router Split

Work order: WO-QLXL-APP-SPLIT-20260727

Status: CLOSED

Risk: R1

## Authority

The operator explicitly requested that governance be cleaned up and both
remaining refactors be completed.

## Authorized Changed Set

Application implementation:

- `backend/app.py`
- `backend/shared.py`
- `backend/vessels_api.py` (new)
- `backend/user_management_api.py` (new)
- `tests/test_backend.py` (structural test ownership update only)
- `scripts/check_unbound_names.py` (accepted review repair: expand globs
  cross-shell and keep failure diagnostics encoding-safe)

Governed evidence/continuity:

- `docs/reviews/APP_ROUTE_EXTRACTION_REVIEW_20260727.md` (new)
- `IMPLEMENTATION_STATUS.json`
- `docs/catalog/MODULE_REGISTRY.json`
- generated `docs/catalog/MODULE_CATALOG.md`
- `CVF_SESSION/ACTIVE_SESSION_STATE.json`
- active handoff

The governance/bootstrap files already changed while repairing the doctor are
also part of the final reviewed changed set, but BUILD must not alter the CVF
core.

Amendment: targeted regression exposed a test that monkeypatched
`backend.app.BACKUP_DIR`. Because backup route ownership moved intact to
`backend.user_management_api`, the authorized test-only adjustment patches the
new owner module. Endpoint behavior and assertions remain unchanged.

Review-repair amendment: the whole-backend checker command exposed that
PowerShell does not expand `backend/*.py` for native programs. The checker will
expand its own glob arguments and use encoding-safe failure labels so the
documented command returns the promised exit code instead of crashing.

## Implementation Sequence

1. Move app-independent shared helpers required by multiple modules.
2. Extract VESSELS request models and route block; register the router.
3. Static-check and independently import the vessel module.
4. Extract USER MANAGEMENT request models and admin route block; keep reverse
   dependency helpers in `app.py`; register the router.
5. Static-check and independently import the user-management module.
6. Compare ordered route identity against `HEAD`.
7. Run targeted tests, then the full suite.

## Evidence Commands

- `python scripts/check_unbound_names.py backend/vessels_api.py backend/user_management_api.py`
- standalone Python imports for both modules;
- an executable comparison of ordered `(methods, path, endpoint name)` tuples
  from `HEAD:backend/app.py` and the working tree;
- targeted pytest selection covering users, backups, reporting units, vessels,
  port register, tenant isolation, and dashboard consumers;
- full `pytest`.

## Stop Conditions

The stop conditions in `SPEC-QLXL-APP-SPLIT-20260727` apply. In addition,
do not commit or push without a separate explicit operator request.

## Roles

- IMPLEMENTATION_WORKER: Codex
- REVIEWER: Codex after an explicit role transition; permitted because this is
  R1, with executable evidence and no hidden dissent.
- COMMIT_STEWARD: Codex, explicitly authorized by the operator.

## Closure

- Operator authorized commit and push.
- Implementation/governance commit:
  `1b2dd1089250dafc316c205645c22d454758952d`.
- Review disposition: PASS.
- Final full suite: 254 passed, 2 warnings.
- Ordered API route identity: 77 before, 77 after, identical.
- Unrelated `.claude/` content was excluded from the commit.
