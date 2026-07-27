# App Route Extraction Review

Review ID: REVIEW-QLXL-APP-SPLIT-20260727

Work order: WO-QLXL-APP-SPLIT-20260727

Disposition: PASS

Reviewer role: REVIEWER

Risk: R1

## Changed Behavior Assessment

No intended application behavior changed. The VESSELS and USER MANAGEMENT
route blocks now live in dedicated `APIRouter` modules. Router inclusion occurs
at the original block positions, before the static mount.

The three reverse-dependent helpers discovered during intake remain in
`backend/app.py`.

## Executable Evidence

- Workspace doctor before BUILD: PASS, 25/25.
- Standalone import:
  `backend.vessels_api`, `backend.user_management_api`, and `backend.app` pass.
- Static checker: every backend Python module reports `OK`.
- AST move comparison:
  - vessel module: 17 moved classes/functions checked;
  - user-management module: 14 moved classes/functions checked;
  - shared helpers: `_clean_email` and `certificate_status` checked;
  - mismatches: none after ignoring only the `app` -> `router` decorators.
- Route identity:
  `BEFORE=77 AFTER=77 IDENTICAL=True` for ordered
  `(sorted methods, path, endpoint name)` tuples.
- Targeted PostgreSQL regression: 48 passed, 126 deselected.
- Final full PostgreSQL suite: 254 passed, 2 warnings in 46.22 seconds.
- `python -m compileall -q backend`: pass.
- `git diff --check`: pass.

The two full-suite warnings are existing openpyxl warnings about unsupported
Data Validation extensions. They are not test failures.

## Findings And Repairs

### Structural backup test

The first targeted run produced 47 passes and one failure because the test
monkeypatched `backend.app.BACKUP_DIR`. The route owner is now
`backend.user_management_api`; the test patch target was updated while keeping
all endpoint assertions unchanged. The rerun passed.

### Static-checker shell contract

Review found that the documented `backend/*.py` command received a literal
glob under PowerShell. The checker now expands glob arguments itself and uses
encoding-safe failure labels.

Repair verification:

- `python scripts/check_unbound_names.py backend/*.py`: pass;
- deliberate negative sample: exit 1, exactly `MISSING ROOT, json`;
- comprehension and `except ... as` bindings were not falsely reported;
- unmatched glob: exit 1 with `NOT FOUND`, no console encoding crash.

## Changed-Set Review

- `backend/app.py` reduced from 3038 to 2102 physical lines.
- `backend/vessels_api.py`: 645 physical lines.
- `backend/user_management_api.py`: 322 physical lines.
- Neither new module imports `backend.app`.
- Imports made newly unused by the extraction were removed; intentional
  compatibility exports that predated the work were preserved.

## Claim Boundary

This is application refactor evidence. It does not claim that CVF governed a
provider or agent behavior, so it does not require or substitute for live
provider-backed governance proof.
