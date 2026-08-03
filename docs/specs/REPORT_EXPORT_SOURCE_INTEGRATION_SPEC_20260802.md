# Report Export Source Integration Specification

Spec ID: SPEC-QLXL-REPORT-EXPORT-SOURCE-20260802

Status: AUTHORIZED_SCOPE

Phase: SPEC

Risk: R2

## API Requirements

1. `GET /api/reports/{kind}` accepts `source=live|historical|combined` and
   defaults to `live` for backward compatibility.
2. PL.01 rejects non-LIVE sources with an explanatory 422 response.
3. Historical PL.02 uses active `COMMITTED`/`REVIEW` imports scoped to the
   current reporting unit and requested month/year-to-date window.
4. Historical PL.02 maps TOS values only to container tonnes, container TEU
   and calls. Unsupported or incomplete metrics remain blank.
5. Historical PL.03 returns one row for each valid Berth call inside the
   requested date range and uses only cargo matched to that call.
6. Combined PL.02/PL.03 rejects with 409 when a requested calendar month has
   both approved LIVE facts and active historical coverage.
7. Combined non-overlapping periods sum supported PL.02 metrics and concatenate
   PL.03 rows without adding blank register-only rows.
8. Tenant/RBAC boundaries remain identical to the existing LIVE and historical
   routes.

## UX Requirements

1. Activity Reports shows one segmented selector labelled
   `Nguồn PL.02 / PL.03` with LIVE, LỊCH SỬ / TOS and KẾT HỢP.
2. PL.01 shows `LIVE cố định` and always exports with `source=live`.
3. PL.02 and PL.03 cards show the currently selected source.
4. A concise source explanation identifies available facts and warns that
   combined output is blocked for overlapping months.
5. The PL.02 adjustment editor is hidden outside LIVE and its state is not
   discarded.
6. The Import-page export is labelled as a quick PL.03 TOS shortcut rather
   than a distinct report definition.
7. Existing date/month controls and default LIVE behavior remain unchanged.

## Validation

- Backward-compatible LIVE export tests.
- PL.01 non-LIVE rejection test.
- PostgreSQL historical PL.02 current/YTD mapping test.
- Historical PL.03 date-range and per-call row test.
- Combined overlap rejection and non-overlap aggregation tests.
- Frontend static/UX tests for a single selector, fixed PL.01 source, dynamic
  PL.02/PL.03 badges, contextual guidance and adjustment visibility.
- Python compile, JavaScript syntax, unbound-name scan, catalog, diff and
  workspace doctor checks.

## Non-Goals

- Reconstructing PL.01 from incomplete historical sources.
- Inventing passenger, dry, liquid or foreign-cargo facts absent from imports.
- Deleting or migrating production data.
- Commit, push, deployment or FREEZE.
