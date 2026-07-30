# Vessel Attachment Access Review

Review ID: REVIEW-QLXL-VESSEL-ATTACHMENT-ACCESS-20260730

Status: PASS_WITH_LIMITATIONS

Risk: R2

## Implemented Scope

- Actionable attachment-count button in both vessel lists.
- Existing vessel modal opens and focuses its attachment section.
- Attachment filenames trigger authenticated browser downloads.
- Tenant-guarded vessel attachment download endpoint.
- Local and MinIO storage reads.
- Forced-download and anti-sniff/sandbox response headers.
- Frontend cache key `1.13.5`.

## Evidence

- Focused Docker PostgreSQL tests: 7 passed.
- Full PostgreSQL 17 client/server suite: 271 passed, 3 warnings, 0 failed.
- Live local API: status 200, exact 35-byte PDF payload,
  `Content-Disposition: attachment`, `nosniff`, and CSP `sandbox`.
- Python compile, JavaScript syntax, catalog check, and diff check: passed.
- Workspace doctor: 25/25.
- Browser skill discovery returned no available browser session, so rendered
  click/download evidence remains unavailable in this environment.

## Review Questions

1. Does every read path enforce canonical vessel tenant scope?
2. Can an attachment id be used with a different vessel id?
3. Can stored keys escape storage roots or leak through API responses?
4. Are quarantined bytes prevented from inline execution?
5. Do frontend event bindings open the correct list context and download the
   intended attachment?

## Independent Findings

- MEDIUM: MinIO `S3Error` for a missing object was not translated to the
  endpoint's controlled `FileNotFoundError`/404 contract.
- LOW: generic `api()` attempted JSON parsing for a successfully downloaded
  file whose stored content type contained `json`, while the downloader
  required a Blob.

Both findings are accepted and returned to BUILD for repair and regression
coverage.

## Repair Evidence

- MinIO missing-key errors now translate to `FileNotFoundError`; adapter
  regression coverage reproduces `S3Error(code="NoSuchKey")`.
- Successful file downloads now explicitly select Blob response handling;
  unsuccessful JSON responses still use the generic API error parser.
- Post-repair focused suite: 8 passed.
- Post-repair full Docker PostgreSQL 17 suite: 272 passed, 3 warnings,
  0 failed.

## Independent Re-review

No HIGH, MEDIUM, or LOW finding remains. The reviewer independently reproduced
MinIO missing errors from both acquisition and stream-read stages, connection
cleanup, a successful JSON-labelled PDF Blob, and a JSON 404 preserving its
server detail.

Disposition: `PASS_WITH_LIMITATIONS`. The only limitation is the unavailable
rendered browser session; no visual click/download proof is claimed.

## Claim Boundary

No production data, deployment, commit, push, merge, or rendered browser proof
is claimed.
