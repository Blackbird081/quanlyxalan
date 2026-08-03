# Historical Snapshot, Per-Call PL.03 And Berth Filter Specification

Spec ID: SPEC-QLXL-HISTORICAL-SNAPSHOT-CALL-BERTH-20260802

Status: AUTHORIZED_SCOPE

Phase: SPEC

Risk: R2

## Functional Requirements

1. Preview classifies a file as `CUMULATIVE_SNAPSHOT` only when its stable
   identity multiset contains the active identity multiset in scope.
2. A cumulative preview stages the complete new workbook; confirmation
   supersedes all conflicting active receipts and preserves updated values.
3. A partial preview stages only new facts and retains explicit incremental
   merge behavior. Missing facts never cause automatic deletion.
4. Only `PLATFORM_ADMIN` may delete a historical import receipt.
5. Delete accepts only `PREVIEWED`, `REJECTED` and `SUPERSEDED`; active
   `COMMITTED` or `REVIEW` receipts return conflict.
6. Delete remains tenant-scoped and refuses a Berth receipt referenced by
   cargo rows owned by another receipt.
7. Historical PL.03 produces exactly one report row per validated Berth call.
8. Cargo totals and ATB/ATD on a PL.03 row belong only to that call; repeated
   Salan identity across voyages must not be collapsed.
9. Berth code is not added to PL.03.
10. Activity analytics and its Excel export accept an optional berth filter.
11. Historical metrics filter by normalized Berth column H; LIVE metrics use
    the corresponding working-port value.
12. The analytics response exposes available berth choices and the applied
    filter; frontend changes reload analytics and export with that filter.

## Security And Integrity Requirements

- All import queries and deletes are reporting-unit scoped.
- Non-admin delete returns 403.
- Protected active receipt delete returns 409.
- Cross-import dependencies return 409 without partial deletion.
- Confirmation and deletion are transactional.
- No source archive or production data is removed during verification.

## Validation

- PostgreSQL API tests for admin/non-admin/protected/dependency delete cases.
- Cumulative and partial snapshot regression tests.
- XLSX regression with one Salan on at least two voyages and per-call cargo.
- Historical analytics and export tests for two berth codes.
- Frontend static/UX tests for delete control and berth selector.
- Python compile, JavaScript syntax, catalog, workspace doctor and diff checks.

## Non-Goals

- No Berth column in PL.03.
- No production cleanup or migration of existing receipts in this tranche.
- No merge, deployment or FREEZE authorization.
