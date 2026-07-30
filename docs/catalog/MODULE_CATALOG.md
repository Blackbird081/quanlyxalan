# Module Catalog

Machine-readable source: `docs/catalog/MODULE_REGISTRY.json`

Status: GOVERNED

## Metrics

- Total modules: 3
- Enforced: 1
- Partial: 2
- Contract-only: 0
- Stub: 0
- Deprecated: 0

| id | status | path | evidence | description |
|---|---|---|---|---|
| historical-import-api | PARTIAL | `backend/historical_api.py` | docs/reviews/HISTORICAL_SOT_AND_VESSEL_ATTACHMENTS_REVIEW_20260729.md; tests/test_sot_merge_unit.py; tests/test_backend.py | Tenant-scoped historical TOS/PL.03 import with source-of-truth retention and incremental merge implemented; PostgreSQL integration and independent R2 review remain pending. |
| user-management-api | ENFORCED | `backend/user_management_api.py` | docs/reviews/APP_ROUTE_EXTRACTION_REVIEW_20260727.md; tests/test_user_management.py; tests/test_backend.py | Platform-admin user, operations-summary, and local-backup API routes extracted from app.py. |
| vessels-api | PARTIAL | `backend/vessels_api.py` | docs/reviews/APP_ROUTE_EXTRACTION_REVIEW_20260727.md; docs/reviews/HISTORICAL_SOT_AND_VESSEL_ATTACHMENTS_REVIEW_20260729.md; tests/test_backend.py; tests/test_sot_merge_unit.py | Reporting-unit, port-register and vessel API, including quarantined vessel attachments; the prior route extraction is enforced while new attachment PostgreSQL evidence remains pending. |
