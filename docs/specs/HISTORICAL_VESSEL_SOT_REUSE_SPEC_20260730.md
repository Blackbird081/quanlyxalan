# Historical Vessel Source-of-Truth Reuse Specification

Spec ID: SPEC-QLXL-HISTORICAL-VESSEL-SOT-REUSE-20260730

Status: AUTHORIZED_SCOPE

Phase: SPEC

Risk: R2

## Requirements

1. A different voyage number creates a new Berth call but does not invalidate
   a known vessel identity.
2. A unique exact or normalized match in the current reporting unit is linked
   automatically with `ACCEPTED` status.
3. The latest Admin-accepted mapping for the same normalized raw TOS name is
   reused when its vessel remains assigned to the current reporting unit.
4. An accepted historical mapping may survive a superseded import, but not a
   rejected or unconfirmed import.
5. A later Admin correction replaces an earlier accepted identity decision;
   disagreement between that latest decision and the current register remains
   `PENDING` and requires review.
6. Unmatched and ambiguous names remain `PENDING`.
7. Automatically accepted calls receive `vessel_id`, contain no vessel-link
   review warning, and are not returned by the pending-link endpoint.
8. Tenant isolation and the incremental call-key merge contract remain
   unchanged.

## Validation

- Unit coverage of accepted-history selection and conflict handling.
- PostgreSQL API coverage for a confirmed vessel followed by a new voyage.
- Existing cumulative-import, tenant-link, and frontend tests.
- Python compile, diff, catalog, and workspace doctor checks.

## Non-Goals

No production data rewrite, fuzzy matching beyond existing normalization,
cross-tenant reuse, automatic conflict resolution, commit, push, merge,
deployment, or FREEZE.
