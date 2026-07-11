# API Contract — Khai-bao-Cang-vu

> Generated: 2026-07-11  
> Tranche: T0 Baseline Recovery (WO-KBCV-T0-20260711)  
> Backend: FastAPI + SQLAlchemy (SQLite local / PostgreSQL production)  
> Auth: JWT Bearer (`Authorization: Bearer <token>`)

## Endpoints

### AUTH

| Method | Path | Auth | Request | Response | Status |
|--------|------|------|---------|----------|--------|
| POST | `/api/auth/login` | None | `{username, password}` | `{access_token, token_type}` | ✅ DONE |

### HEALTH + CATALOGS

| Method | Path | Auth | Request | Response | Status |
|--------|------|------|---------|----------|--------|
| GET | `/api/health` | None | — | `{status, database, version}` | ✅ DONE |
| GET | `/api/catalogs` | None | — | `{vesselTypes, vesselClasses, shellMaterials, cargoTypes, unloadMovements, loadMovements}` | ✅ DONE |

### ORGANIZATIONS

| Method | Path | Auth | Request | Response | Status |
|--------|------|------|---------|----------|--------|
| GET | `/api/organizations` | Bearer | — | `[Organization]` | ✅ DONE |

### DASHBOARD

| Method | Path | Auth | Request | Response | Status |
|--------|------|------|---------|----------|--------|
| GET | `/api/dashboard?q=` | Bearer | query `q` (optional) | `{stats, recent, matches}` | ✅ DONE |

### VESSELS

| Method | Path | Auth | Request | Response | Status |
|--------|------|------|---------|----------|--------|
| GET | `/api/vessels` | Bearer | — | `[Vessel]` | ✅ DONE |
| POST | `/api/vessels` | Bearer | `VesselSaveRequest` | `Vessel` | ✅ DONE |
| POST | `/api/vessels/{id}/verify-registry` | Bearer | — | `Vessel` | ✅ DONE (local only) |

> **Note (ADR-001)**: Registry verification at `/api/vessels/{id}/verify-registry` is local-only in T0.
> It checks the internal certificate date and records `source=local`. Real Maritime Authority
> registry API integration is deferred to T6 pending official API contract.

### CREW

| Method | Path | Auth | Request | Response | Status |
|--------|------|------|---------|----------|--------|
| GET | `/api/crew` | Bearer | — | `[CrewMember]` | ✅ DONE |
| POST | `/api/crew` | Bearer | `CrewSaveRequest` | `CrewMember` | ✅ DONE |

### DECLARATIONS

| Method | Path | Auth | Request | Response | Status |
|--------|------|------|---------|----------|--------|
| GET | `/api/declarations` | Bearer | query filters | `[Declaration]` | ✅ DONE |
| POST | `/api/declarations?submit=false` | Bearer | `DeclarationSaveRequest` | `Declaration` | ✅ DONE |
| POST | `/api/declarations?submit=true` | Bearer | `DeclarationSaveRequest` | `Declaration` (workflow_status=PENDING_REVIEW) | ✅ DONE |
| POST | `/api/declarations/{id}/attachments?filename=` | Bearer | raw file body | `Attachment` | ✅ DONE |
| GET | `/api/declarations/{id}/events` | Bearer | — | `[DeclarationEvent]` | ✅ DONE |
| POST | `/api/declarations/{id}/workflow` | Bearer | `WorkflowActionRequest` | `Declaration` | ✅ DONE |

#### Workflow state machine

```
DRAFT → PENDING_REVIEW  (on submit=true)
PENDING_REVIEW → PENDING_QLC  (CV_APPROVE)
PENDING_QLC → PENDING_BP  (QLC_APPROVE)
PENDING_BP → APPROVED  (BP_APPROVE)
APPROVED → ISSUED  (ISSUE, requires permit_no)
any → CHANGES_REQUESTED  (REQUEST_CHANGES, requires note)
any → REVOKED  (REVOKE, requires note)
```

### SUGGESTIONS

| Method | Path | Auth | Request | Response | Status |
|--------|------|------|---------|----------|--------|
| GET | `/api/suggestions?field=` | Bearer | `field` ∈ {last_port, working_port, destination_port, master_name} | `[string]` | ✅ DONE |

### IMPORT

| Method | Path | Auth | Request | Response | Status |
|--------|------|------|---------|----------|--------|
| POST | `/api/import/vessels` | Bearer | XLSX body | `{accepted, rejected}` | ✅ DONE |
| POST | `/api/import/declaration` | Bearer | XLSX body | `{accepted, rejected, id}` | ✅ DONE |

> XLSX files are validated by magic bytes (PK\x03\x04) before parsing.

### REPORTS

| Method | Path | Auth | Request | Response | Status |
|--------|------|------|---------|----------|--------|
| GET | `/api/reports/appendix1?from=&to=` | Bearer | date range | XLSX download | ✅ DONE |
| GET | `/api/reports/appendix2?from=&to=` | Bearer | date range | XLSX download | ✅ DONE |
| GET | `/api/reports/appendix3?from=&to=` | Bearer | date range | XLSX download | ✅ DONE |

### INTEGRATIONS

| Method | Path | Auth | Request | Response | Status |
|--------|------|------|---------|----------|--------|
| GET | `/api/integrations/maritime-authority` | Bearer | — | `{connector, jobs}` | ✅ DONE |
| POST | `/api/integrations/prepare-sync` | Bearer | `{from, to}` | `{id, recordCount, status}` | ✅ DONE (PREPARED only) |

> **IMPORTANT**: `/api/integrations/prepare-sync` creates a `PREPARED` SyncJob but does **not**
> send any data to external systems. External sync is out of scope until T6 (requires official
> Maritime Authority API contract, credentials, sandbox and data-sharing approval).

## Attachment rules

| Property | Limit |
|----------|-------|
| Max size | 12 MB |
| Allowed extensions | .jpg, .jpeg, .png, .webp, .pdf, .doc, .docx, .xls, .xlsx |
| Magic byte check | Yes — extension must match file header |

## Error shape

All errors return JSON: `{"detail": "<message>"}` (FastAPI standard).

## Disabled / deferred features

| Feature | Status | Reason |
|---------|--------|--------|
| Real registry API verification | DISABLED (returns local only) | No official API contract (T6) |
| External Maritime Authority sync send | DISABLED (prepare-only) | No credentials or sandbox (T6) |
| RBAC / tenant isolation | PARTIAL (auth exists, authorization gaps noted) | Deferred to T1 |
| HTTPS / security headers | DEFERRED | Production ops concern (T4) |
