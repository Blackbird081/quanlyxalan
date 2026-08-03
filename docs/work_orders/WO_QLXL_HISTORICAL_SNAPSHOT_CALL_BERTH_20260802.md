# Work Order: Historical Snapshot, Per-Call PL.03 And Berth Analytics

Work order: WO-QLXL-HISTORICAL-SNAPSHOT-CALL-BERTH-20260802

Status: AUTHORIZED_FOR_BUILD

Risk: R2

## Authority

The operator authorized Platform Admin cleanup of obsolete import history,
clarified that PL.03 from TOS must keep one row per Salan voyage/timeline, and
clarified that Berth column H belongs in Activity Report filtering rather than
the PL.03 output.

## Authorized Changed Set

- `backend/historical_api.py`
- `backend/reports_api.py`
- `frontend/app.js`
- `frontend/index.html`
- `frontend/styles.css` only if needed for the new controls
- `tests/test_backend.py`
- `tests/test_frontend_ux.py`
- governed DESIGN/SPEC/WORK_ORDER/REVIEW and continuity truth

No schema migration is authorized unless implementation proves one is
strictly required; the current model already stores call key and berth code.

## Acceptance

The twelve functional requirements in the specification pass executable
tests. Existing tenant isolation, historical reconciliation, report coverage,
and cumulative multiplicity tests remain passing.

## Stop Conditions

Stop if snapshot containment cannot preserve cargo multiplicity, deleting one
receipt could cascade into an active receipt, tenant scope is ambiguous, or
per-call export cannot bind cargo to one validated call.

## Roles And Publication Boundary

- ORCHESTRATOR / SPEC_AUTHOR / WORK_ORDER_AUTHOR: current agent.
- IMPLEMENTATION_WORKER: current agent after recorded BUILD acknowledgment.
- REVIEWER: current agent may perform source/test review because no independent
  agent was requested, but R2 limitations and failed checks must be explicit.

Commit, push, merge, deployment, production cleanup and FREEZE are not
authorized.
