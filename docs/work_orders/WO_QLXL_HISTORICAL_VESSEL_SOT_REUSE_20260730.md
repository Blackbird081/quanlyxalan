# Work Order: Historical Vessel Source-of-Truth Reuse

Work order: WO-QLXL-HISTORICAL-VESSEL-SOT-REUSE-20260730

Status: REVIEWED_AWAITING_OPERATOR

Risk: R2

## Authority

The operator established that Admin-verified or Admin-maintained vessel
identity is source of truth. A changed voyage number must not force repeated
confirmation when the vessel identity is otherwise unchanged.

## Authorized Changed Set

- `backend/historical_api.py`
- focused historical-import tests
- this tranche's decision, specification, work order, review,
  implementation-truth, and active continuity files

Existing attachment-preview changes and `.claude/` are outside this work
order and must be preserved without inclusion in this implementation claim.

## Acceptance

1. A new voyage for a known vessel is automatically linked.
2. Unique current-register matches and unambiguous accepted history are reused.
3. Conflicts, ambiguity, and foreign-tenant candidates remain reviewable.
4. Incremental SOT row filtering remains based on call identity.
5. Focused and full regression evidence pass, subject only to documented
   environment limitations.

## Roles

ORCHESTRATOR -> SPEC_AUTHOR -> WORK_ORDER_AUTHOR ->
IMPLEMENTATION_WORKER -> REVIEWER -> ORCHESTRATOR.

## Stop Conditions

Stop on cross-tenant reuse, ambiguous auto-acceptance, production mutation, or
need for a schema migration. Commit, push, merge, deployment, and FREEZE are
not authorized.
