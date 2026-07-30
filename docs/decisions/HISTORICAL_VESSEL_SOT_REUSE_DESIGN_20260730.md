# Historical Vessel Source-of-Truth Reuse Design

Decision ID: ADR-QLXL-HISTORICAL-VESSEL-SOT-REUSE-20260730

Status: APPROVED_BY_OPERATOR_SCOPE

Phase: DESIGN

Risk: R2

## Intent

Treat a tenant-scoped vessel profile maintained by an Admin, and an Admin's
accepted historical vessel link, as source-of-truth identity evidence. A new
Berth call may have a different voyage number without requiring the same
vessel identity to be confirmed again.

## Decision

- Keep call deduplication keyed by normalized vessel name, year, and voyage.
  A different voyage remains a new operational call.
- Resolve vessel identity independently from call identity.
- Automatically accept a unique exact or normalized match against the current
  tenant-scoped vessel register.
- Reuse the latest Admin-accepted link for the same normalized TOS vessel name
  when it points to a current tenant-scoped vessel; a later Admin correction
  becomes the new source of truth.
- If the latest accepted decision conflicts with the current unique register
  match, require manual review.
- Never reuse a link to a vessel outside the current reporting unit.
- Preserve manual review for unmatched and ambiguous names.

## Claim Boundary

This decision governs local historical-import identity reconciliation. It does
not mutate production data or claim live AI-governance behavior.
