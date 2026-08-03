# Module Catalog

Machine-readable source: `docs/catalog/MODULE_REGISTRY.json`

Status: GOVERNED

## Metrics

- Total modules: 4
- Enforced: 1
- Partial: 3
- Contract-only: 0
- Stub: 0
- Deprecated: 0

| id | status | path | evidence | description |
|---|---|---|---|---|
| activity-reports-api | PARTIAL | `backend/reports_api.py` | docs/reviews/HISTORICAL_SNAPSHOT_CALL_ROWS_BERTH_FILTER_REVIEW_20260802.md; docs/reviews/REPORT_EXPORT_SOURCE_INTEGRATION_REVIEW_20260802.md; docs/reviews/REPORT_SOURCE_UI_UX_TEST_REPORT_20260803.md; tests/test_backend.py; tests/test_frontend_ux.py | Activity analytics and Excel exports support explicit LIVE, historical/TOS and overlap-protected combined sources for PL.02/PL.03, while PL.01 remains LIVE-only; historical analytics also filters by normalized Berth column H. Local rendered-browser evidence is recorded while production evidence remains outside scope. |
| historical-import-api | PARTIAL | `backend/historical_api.py` | docs/reviews/HISTORICAL_SNAPSHOT_CALL_ROWS_BERTH_FILTER_REVIEW_20260802.md; docs/reviews/REPORT_SOURCE_UI_UX_TEST_REPORT_20260803.md; tests/test_sot_merge_unit.py; tests/test_backend.py; tests/test_frontend_ux.py | Tenant-scoped historical TOS/PL.03 import with cumulative-snapshot replacement, safe partial merge, Admin-only inactive-history deletion and one PL.03 row per Berth call; local browser and PostgreSQL evidence are recorded while production evidence remains outside scope. |
| user-management-api | ENFORCED | `backend/user_management_api.py` | docs/reviews/APP_ROUTE_EXTRACTION_REVIEW_20260727.md; tests/test_user_management.py; tests/test_backend.py | Platform-admin user, operations-summary, and local-backup API routes extracted from app.py. |
| vessels-api | PARTIAL | `backend/vessels_api.py` | docs/reviews/APP_ROUTE_EXTRACTION_REVIEW_20260727.md; docs/reviews/HISTORICAL_SOT_AND_VESSEL_ATTACHMENTS_REVIEW_20260729.md; tests/test_backend.py; tests/test_sot_merge_unit.py | Reporting-unit, port-register and vessel API, including quarantined vessel attachments; the prior route extraction is enforced while new attachment PostgreSQL evidence remains pending. |
