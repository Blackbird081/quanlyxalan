# Work Order: Admin-only Data Tabs

Work order: WO-QLXL-ADMIN-ONLY-DATA-TABS-20260730

Status: LOCAL_COMMIT_CREATED

Risk: R2

## Authority

The operator directed that `Import dữ liệu` and `Báo cáo hoạt động` be
admin-only tabs, hidden from every other role, and that the user-visible word
`Revision` be translated consistently into Vietnamese.

## Authorized Changed Set

- `frontend/app.js`
- `frontend/index.html`
- `USER_GUIDE.md`
- focused tests under `tests/test_frontend_ux.py` and `tests/test_backend.py`
- this tranche's decision, specification, work order, review, implementation
  truth, and active continuity files

## Acceptance

1. Both navigation items are visible only for Platform Admin.
2. Non-admin direct hash access is redirected to an allowed page without
   calling the restricted page loaders.
3. Platform Admin behavior remains unchanged.
4. User-visible historical import UI consistently says `Bản sửa đổi`.
5. Existing user-owned edits are preserved.
6. Focused tests, JavaScript syntax, diff, catalog, and doctor checks pass.

## Roles And Sequence

- ORCHESTRATOR completed INTAKE and classified the change as R2.
- SPEC_AUTHOR completed DESIGN and SPEC.
- WORK_ORDER_AUTHOR bounded the changed set, acceptance, evidence, and stop
  conditions.
- IMPLEMENTATION_WORKER may now enter BUILD.
- The same agent may transition to REVIEWER only with explicit executable
  evidence because this is a bounded frontend RBAC change; no claim of
  independent review will be made.

## Stop Conditions

Stop BUILD if implementation requires backend authorization changes, breaks
another role's permitted landing page, overwrites existing user edits, or
expands beyond the authorized files. Commit, push, merge, deployment, and
FREEZE are not authorized.

## Documentation And Commit Amendment

On 2026-07-30 the operator requested a User Guide explanation that the LIVE
PL.03 export and the historical/TOS PL.03 export are separate workflows, and
authorized committing the reviewed changed set. The operator's manual copy
cleanup in the already-scoped frontend files is accepted as the intended
working version. COMMIT_STEWARD may create one local commit containing the
reviewed tracked changed set and governed artifacts. Push, merge, deployment,
FREEZE, and untracked `.claude/` remain excluded.
