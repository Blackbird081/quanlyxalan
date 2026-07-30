# Vessel Attachment Preview Specification

Spec ID: SPEC-QLXL-VESSEL-ATTACHMENT-PREVIEW-20260730

Status: AUTHORIZED_SCOPE

Phase: SPEC

Risk: R2

## Functional Requirements

1. Selecting an attachment filename opens a preview dialog and does not
   download automatically.
2. PNG, JPEG, WebP, and PDF attachments are fetched through the existing
   authenticated vessel attachment endpoint and shown in the dialog.
3. PDF content is hosted in a sandboxed iframe.
4. Word and Excel attachments show an unsupported-preview message without
   fetching bytes until the user chooses download.
5. `Tải xuống` explicitly downloads the selected attachment.
6. Closing or replacing a preview revokes its object URL.
7. Preview loading and errors are announced in the dialog.
8. Existing delete, upload, tenant guard, missing-object, and forced-download
   behavior remain unchanged.

## Compatibility Requirements

- Preserve the existing endpoint and response security headers.
- Preserve operator-authored frontend copy and untracked `.claude/`.
- Advance both frontend asset cache keys together.
- Provide usable mobile sizing and keyboard-accessible dialog actions.

## Validation

- Focused frontend UX tests.
- Existing vessel attachment backend test against PostgreSQL 17.
- JavaScript syntax, diff, catalog, and workspace doctor checks.
- Browser-rendered popup verification when available.

## Non-Goals

No Office-to-HTML conversion, public URL, inline SVG/HTML preview, scanner
policy change, migration, commit, push, merge, deployment, or FREEZE.
