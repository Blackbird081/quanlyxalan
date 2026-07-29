# Work Order: Historical SOT Merge And Vessel Attachments

Work order: WO-QLXL-SOT-ATTACHMENTS-20260729

Status: REPAIR_REVIEWED_CHECKPOINT

Risk: R2

## Authority

The operator requested a file-attachment area when Admin supplements a Salan
profile and required the manually confirmed database to remain the source of
truth when cumulative Berth, Salan-detail and PL.03 files are imported again
with additional vessels.

## Authorized Changed Set

Application and migration:

- `backend/models.py`
- `backend/storage.py`
- `backend/vessels_api.py`
- `backend/historical_api.py`
- `backend/app.py` only if shared attachment wiring must move
- successor migrations under `alembic/versions/`; published revisions remain
  immutable and repair schema changes require a new head
- `frontend/app.js`
- `frontend/index.html` for vessel-attachment UI wiring
- `frontend/styles.css` only for attachment presentation

Tests:

- `tests/test_backend.py`
- `tests/test_historical_import.py`
- `tests/test_frontend_ux.py`
- focused storage/migration tests if required

Governed artifacts and continuity:

- this work order and its DESIGN/SPEC/REVIEW artifacts
- `IMPLEMENTATION_STATUS.json`
- catalog sources/generated views if module truth changes
- `CVF_SESSION/ACTIVE_SESSION_STATE.json`
- active handoff

## Implementation Sequence

1. Generalize attachment ownership and add vessel attachment endpoints.
2. Add the vessel-modal attachment list/upload flow.
3. Add tenant-scoped SOT duplicate classification for all three historical
   source kinds, including cargo multiset handling.
4. Add `MERGE_NEW_RECORDS`, receipt counts and active incremental report
   composition while preserving explicit revision behavior.
5. Run targeted tests, repair accepted findings within this changed set, then
   run the full suite.

## Evidence Commands

- focused pytest selections for vessel attachments and historical cumulative
  imports;
- `python -m compileall -q backend`;
- full `pytest`;
- `powershell -ExecutionPolicy Bypass -File scripts/manage_cvf_downstream_catalog.ps1 -Check`;
- workspace doctor;
- `git diff --check`.

## Roles

- ORCHESTRATOR / SPEC_AUTHOR / WORK_ORDER_AUTHOR: current agent.
- IMPLEMENTATION_WORKER: current agent after recorded transition.
- REVIEWER: `/root/independent_review`, independent from the implementation
  worker because this is R2.
- COMMIT_STEWARD: current agent, explicitly authorized by the operator on
  2026-07-29 to publish a WIP continuation checkpoint.

## Stop Conditions

The specification stop conditions apply. Do not commit, push, deploy, delete
production data, or claim tranche closure without independent review evidence.

## Checkpoint Amendment

The operator explicitly deferred unavailable PostgreSQL admin evidence so the
work can continue on another machine. Independent review disposition is
`ACCEPT_CHECKPOINT_WITH_LIMITATIONS`. Commit/push is authorized only for this
WIP branch checkpoint; PostgreSQL evidence and all open review findings remain
mandatory before FREEZE or production approval.

## Authorized Repair Scope

The operator directed repair of every independent-review finding:

1. scope PL.03 SOT duplicate identity to its reporting period;
2. make full revision supersede every overlapping active incremental receipt;
3. compensate storage when upload persistence fails;
4. avoid deleting the stored object before the database delete commits;
5. add regression tests and update review/continuity evidence.

Role: REPAIR_WORKER. Phase: BUILD.

Independent re-review found that published revision `x23f0f000023` must remain
immutable. The repair therefore adds successor `y24f0f000024` for
period-scoped historical idempotency.
