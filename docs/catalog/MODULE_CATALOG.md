# Module Catalog

Machine-readable source: `docs/catalog/MODULE_REGISTRY.json`

Status: GOVERNED

## Metrics

- Total modules: 2
- Enforced: 2
- Partial: 0
- Contract-only: 0
- Stub: 0
- Deprecated: 0

| id | status | path | evidence | description |
|---|---|---|---|---|
| user-management-api | ENFORCED | `backend/user_management_api.py` | docs/reviews/APP_ROUTE_EXTRACTION_REVIEW_20260727.md; tests/test_user_management.py; tests/test_backend.py | Platform-admin user, operations-summary, and local-backup API routes extracted from app.py. |
| vessels-api | ENFORCED | `backend/vessels_api.py` | docs/reviews/APP_ROUTE_EXTRACTION_REVIEW_20260727.md; tests/test_backend.py; tests/test_rbac.py; tests/test_port_operations.py | Reporting-unit, port-register, and vessel API routes extracted from app.py. |
