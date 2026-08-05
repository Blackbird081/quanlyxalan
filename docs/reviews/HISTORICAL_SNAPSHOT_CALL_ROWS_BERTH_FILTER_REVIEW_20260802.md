# Historical Snapshot, Per-Call PL.03 And Berth Filter Review

Review ID: REVIEW-QLXL-HISTORICAL-SNAPSHOT-CALL-BERTH-20260802

Work order: WO-QLXL-HISTORICAL-SNAPSHOT-CALL-BERTH-20260802

Disposition: PASS_WITH_LIMITATIONS

Risk: R2

## Scope Review

- A cumulative workbook is recognized only when its stable identity multiset
  contains every active identity in the relevant source/period scope.
- A cumulative confirmation activates the entire new workbook and supersedes
  all conflicting active receipts. Updated values in the newer snapshot win.
- A workbook missing active identities remains a partial increment. Only new
  facts are staged and the existing active facts remain available.
- The backend rejects mismatched confirmation actions: cumulative snapshots
  cannot be merged as increments, and partial increments cannot replace a
  complete snapshot.
- Only Platform Admin can delete inactive `PREVIEWED`, `REJECTED`, or
  `SUPERSEDED` receipts. Active receipts and cross-import Berth dependencies
  are protected; tenant scope is applied to every lookup.
- Source archives are deliberately retained when the visible/database history
  receipt is deleted, preserving recovery and audit boundaries.
- Historical PL.03 now emits one row per validated Berth call. Cargo metrics
  and ATB/ATD remain call-specific when one Salan has multiple voyages.
- Berth code is not written into PL.03.
- Activity analytics and its Excel export apply the same normalized berth
  filter. Historical choices come from Berth column H; LIVE choices use the
  corresponding operational berth/working-port value.

## Review Finding And Repair

- MEDIUM: the frontend selected the correct confirmation action, but a direct
  API client could request `MERGE_NEW_RECORDS` for a cumulative snapshot,
  leaving old and replacement facts active together. The backend now rejects
  that combination with HTTP 409. Regression coverage exercises both invalid
  action directions and the valid partial/cumulative paths.
- Re-review result: the finding is resolved. No open HIGH, MEDIUM, or LOW
  finding remains in the reviewed changed set.

## Executable Evidence

- PostgreSQL 17 regression: 280 passed, 2 deselected, 2 existing openpyxl
  warnings.
- Focused delete, snapshot-action, per-call PL.03 and berth-filter scenarios:
  passed.
- Frontend UX/static suite: 18 passed.
- Python compile, JavaScript syntax, unbound-name scan and `git diff --check`:
  passed.

## Limitations

- Two existing backup tests were deselected because the host does not provide
  the required `pg_dump` executable. They are unrelated to this changed set.
- No connected browser session was available for rendered UI evidence; source,
  API, XLSX and static frontend checks passed.
- No production receipt, source archive, or production data was deleted.
- Commit, push, merge, deployment and FREEZE remain unauthorized.

## Claim Boundary

This review covers local application data behavior and tenant/RBAC controls.
It makes no claim that CVF governs AI or agent behavior and therefore requires
no live provider evidence.
