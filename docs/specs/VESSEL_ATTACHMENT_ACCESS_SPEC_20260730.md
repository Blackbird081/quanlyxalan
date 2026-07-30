# Vessel Attachment Access Specification

Spec ID: SPEC-QLXL-VESSEL-ATTACHMENT-ACCESS-20260730

Status: AUTHORIZED_SCOPE

Phase: SPEC

Risk: R2

## Functional Requirements

1. A vessel row with attachments exposes a keyboard-accessible attachment
   button carrying the existing count and accessible label.
2. Activating the button opens that vessel's editor and focuses the attachment
   section.
3. Existing attachment names can be activated to download their stored bytes.
4. The download endpoint returns the original filename and recorded content
   type without exposing the storage object key.

## Security Requirements

- Reuse the canonical vessel-scope guard before attachment lookup/storage read.
- Require the attachment id to belong to the route vessel id.
- Force `Content-Disposition: attachment`.
- Return `X-Content-Type-Options: nosniff` and `Content-Security-Policy:
  sandbox`.
- Convert missing stored objects into a controlled 404 response.
- Do not put attachment bytes or storage keys in audit messages or API JSON.

## Validation

- Focused backend storage/API tests.
- Focused frontend contract tests and JavaScript syntax check.
- Docker PostgreSQL integration test.
- Rendered browser click/download verification.
- Full suite, compile, catalog, doctor, and diff checks before publication.

## Non-Goals

No inline preview, scanner-policy change, migration, production data mutation,
commit, push, merge, or deployment.
