# Historical SOT And Vessel Attachments Review

Review ID: REVIEW-QLXL-SOT-ATTACHMENTS-20260729

Work order: WO-QLXL-SOT-ATTACHMENTS-20260729

Disposition: ACCEPT_CHECKPOINT_WITH_LIMITATIONS

Risk: R2

Reviewer role: INDEPENDENT_REVIEWER `/root/independent_review`

## Implemented Changed Set

- Vessel attachments now have exactly-one-owner schema semantics, a successor
  migration, tenant-scoped list/upload/delete endpoints, quarantine/scanner
  controls, and vessel-modal UI.
- Historical preview compares cumulative Berth, cargo-detail and reported
  PL.03 rows against active confirmed SOT data.
- Repeated SOT rows are retained and excluded from the new preview counts.
- Cargo matching preserves multiplicity.
- `MERGE_NEW_RECORDS` activates only staged additions without superseding prior
  active imports.
- Explicit revision reparses the archived immutable source and remains
  reason-required.
- PL.03 composition reads all active incremental receipts.

## Executable Evidence Available

- Workspace doctor before BUILD: PASS, 25/25.
- `python -m pytest tests/test_sot_merge_unit.py tests/test_frontend_ux.py -q`:
  20 passed, 1 dependency deprecation warning.
- `python -m pytest tests/test_historical_tos_parser.py tests/test_storage.py -q`:
  9 passed.
- Combined affected non-PostgreSQL run on 2026-07-29:
  `python -m pytest tests/test_sot_merge_unit.py tests/test_frontend_ux.py
  tests/test_historical_tos_parser.py tests/test_storage.py -q`: 29 passed,
  1 dependency deprecation warning.
- Wider non-application-DB selection: 32 passed; two tests requiring the
  PostgreSQL `pg_url` fixture stopped at environment setup.
- `python -m compileall -q backend tests`: pass.
- `python scripts/check_unbound_names.py backend/*.py`: every backend module
  pass.
- `python -c "import backend.app"`: pass; 80 `/api` routes loaded.
- `node --check frontend/app.js`: pass.
- `git diff --check`: pass.

## Required Evidence Still Missing

The PostgreSQL API/migration suite cannot create its throwaway databases.
Both the default test admin URL and the local `.env`-derived URL fail with:

`fe_sendauth: no password supplied`

A full `python -m pytest -q` retry on 2026-07-29 confirmed the same environment
blocker during collection of five PostgreSQL-backed modules; no test assertion
ran or failed in those modules.

The following new/affected tests exist but have not executed in this
environment:

- vessel attachment upload/list/tenant-denial/delete API flow;
- cumulative Berth/cargo/PL.03 SOT merge API flow;
- explicit full-revision regression;
- Alembic head upgrade and exactly-one-owner migration assertions;
- full application suite.

Run with a create-database-capable, secret-safe `TEST_ADMIN_DATABASE_URL`:

```powershell
$env:TEST_ADMIN_DATABASE_URL = "<secret PostgreSQL admin URL>"
python -m pytest -q
```

Do not record the URL value in review artifacts or shell output.

## Independent Review Gate

The independent R2 reviewer accepted publication only as a WIP continuation
checkpoint. This is not a PASS disposition and does not authorize FREEZE,
production deployment, or a functional-completion claim.

### Open reviewer findings

1. HIGH: PL.03 SOT duplicate identity is not period-scoped, so the same Salan
   in a later reporting period can be suppressed as an old row.
2. HIGH: full revision can supersede only one selected import while leaving
   other active incremental receipts overlapping with the restaged full file.
3. MEDIUM: attachment deletion removes storage before the database transaction
   commits, so commit failure can leave a database row pointing to a missing
   object.
4. MEDIUM: attachment upload writes storage before database persistence and
   lacks cleanup if scanning or persistence fails.
5. EVIDENCE: PostgreSQL migration, constraints and API flows remain unverified.

The reviewer also accepted `frontend/index.html` as necessary UI wiring for
this checkpoint; the work-order amendment records that scope clarification.

## Claim Boundary

This pending review records source and local executable evidence only. It does
not claim production deployment, successful PostgreSQL migration, or live CVF
provider governance.
