# Work Order: Vessel Attachment Access

Work order: WO-QLXL-VESSEL-ATTACHMENT-ACCESS-20260730

Status: PR_READY_AWAITING_OWNER_REVIEW

Risk: R2

## Authority

The operator reported that the visible vessel attachment indicator cannot be
clicked to inspect the file and directed that the defect be handled.

## Authorized Changed Set

- `backend/storage.py`
- `backend/vessels_api.py`
- `frontend/app.js`
- `frontend/styles.css`
- `frontend/index.html`
- focused tests under `tests/`
- this tranche's decision, specification, work order, review, implementation
  truth, and active continuity files

## Acceptance

1. The row indicator is actionable and opens the correct vessel attachment
   area.
2. An authorized same-scope user can download the selected file.
3. Cross-tenant, wrong-vessel, and missing-object reads fail safely.
4. Download headers prevent inline execution/sniffing of quarantined content.
5. Existing upload/list/delete behavior remains green.
6. Frontend assets use one advanced cache key.

## Roles And Sequence

- ORCHESTRATOR completed INTAKE and risk classification.
- SPEC_AUTHOR completed DESIGN and SPEC.
- WORK_ORDER_AUTHOR bounded this changed set and evidence.
- IMPLEMENTATION_WORKER may now enter BUILD.
- Independent REVIEWER is required before publication because this is R2.

## Stop Conditions

Stop BUILD on any cross-tenant access, storage-key exposure, inline execution
of quarantined content, regression in upload/delete, or need for a migration.
Commit, push, merge, deployment, and FREEZE are not authorized by this work
order.

## Publication Amendment

On 2026-07-30 the operator explicitly authorized commit and PR creation after
independent repair re-review. COMMIT_STEWARD may commit the reviewed changed
set, push `Blackbird081/quanlyxalan:fix/vessel-attachment-download`, create or
update one PR targeting `hoangnmr/quanlyxalan:main`, and monitor its quality
gate. User-owned `.claude/`, merge, deployment, and FREEZE remain excluded.
