# Vessel Attachment Preview Design

Decision ID: ADR-QLXL-VESSEL-ATTACHMENT-PREVIEW-20260730

Status: APPROVED_BY_OPERATOR_SCOPE

Phase: DESIGN

Risk: R2

## Intent

Replace automatic attachment download on filename click with an explicit
preview dialog. Download occurs only after the user chooses `Tải xuống`.

## Security Decision

- Reuse the existing authenticated, vessel-scoped download endpoint; do not
  introduce a public file URL or expose storage keys.
- Fetch previewable bytes with the same bearer token and reporting-unit header.
- Render only allowlisted raster images (`.jpg`, `.jpeg`, `.png`, `.webp`) in
  an image element and PDF in a sandboxed iframe.
- Do not render Word or Excel bytes as HTML. Their dialog explains that direct
  preview is unavailable and offers an explicit download action.
- Revoke every object URL when the dialog closes or another attachment opens.
- Keep the backend response protections (`attachment`, `nosniff`, `sandbox`)
  unchanged.

## UX Decision

Filename click opens a modal with filename, size, quarantine status, loading or
unsupported state, preview content when safe, and separate `Đóng` /
`Tải xuống` actions. Preview failure remains in the dialog and never triggers
an automatic download.

## Verification

Focused frontend contract tests, JavaScript syntax, static backend attachment
security regression, diff/catalog/doctor checks, and rendered browser evidence
when a connected session is available.

## Claim Boundary

This design covers local application attachment behavior only. It makes no
live AI-governance claim.
