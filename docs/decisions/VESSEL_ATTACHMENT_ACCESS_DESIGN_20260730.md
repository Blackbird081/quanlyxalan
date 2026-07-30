# Vessel Attachment Access Design

Decision ID: ADR-QLXL-VESSEL-ATTACHMENT-ACCESS-20260730

Status: APPROVED_BY_OPERATOR_SCOPE

Phase: DESIGN

Risk: R2

## Intent

Make the existing vessel attachment indicator actionable so an authorized
operator can inspect which files belong to a Salan profile and download a
selected file.

## Decision

- The attachment count is a real button, not a decorative span.
- Activating it opens the existing vessel editor, where the attachment list is
  already tenant-scoped and supports deletion.
- Each attachment name is a download button.
- A new authenticated download endpoint validates the vessel scope and the
  attachment/vessel relationship before reading storage.
- Quarantined files are always returned as downloads, never inline, with
  `X-Content-Type-Options: nosniff` and a sandbox content-security policy.
- Storage adapters expose a bounded `get()` operation; storage object keys
  remain server-only metadata.

## Verification

Backend tests cover successful bytes/headers, cross-tenant denial, mismatched
attachment denial, and missing storage. Frontend tests cover actionable
indicators, attachment downloads, and cache-key synchronization. Browser
verification exercises the rendered click path.

## Claim Boundary

This decision concerns application file access only and does not assert AI
governance behavior.
