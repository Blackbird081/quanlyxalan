# Historical SOT And Vessel Attachments Review

Review ID: REVIEW-QLXL-SOT-ATTACHMENTS-20260729

Work order: WO-QLXL-SOT-ATTACHMENTS-20260729

Disposition: ACCEPT_REPAIR_CHECKPOINT_WITH_PG_LIMITATION

Risk: R2

Reviewer role: INDEPENDENT_REVIEWER `/root/independent_review`

## Implemented Changed Set

- Vessel attachments now have exactly-one-owner schema semantics, a successor
  migration, tenant-scoped list/upload/delete endpoints, quarantine/scanner
  controls, and vessel-modal UI.
- Historical preview compares cumulative Berth, cargo-detail and reported
  PL.03 rows against active confirmed SOT data.
- Repeated SOT rows are retained and excluded from the new preview counts.
- Cargo matching preserves multiplicity.
- `MERGE_NEW_RECORDS` activates only staged additions without superseding prior
  active imports.
- Explicit revision reparses the archived immutable source and remains
  reason-required.
- PL.03 composition reads all active incremental receipts.

## Executable Evidence Available

- Workspace doctor before BUILD: PASS, 25/25.
- `python -m pytest tests/test_sot_merge_unit.py tests/test_frontend_ux.py -q`:
  20 passed, 1 dependency deprecation warning.
- `python -m pytest tests/test_historical_tos_parser.py tests/test_storage.py -q`:
  9 passed.
- Combined affected non-PostgreSQL run on 2026-07-29:
  `python -m pytest tests/test_sot_merge_unit.py tests/test_frontend_ux.py
  tests/test_historical_tos_parser.py tests/test_storage.py -q`: 29 passed,
  1 dependency deprecation warning.
- Wider non-application-DB selection: 32 passed; two tests requiring the
  PostgreSQL `pg_url` fixture stopped at environment setup.
- `python -m compileall -q backend tests`: pass.
- `python scripts/check_unbound_names.py backend/*.py`: every backend module
  pass.
- `python -c "import backend.app"`: pass; 80 `/api` routes loaded.
- `node --check frontend/app.js`: pass.
- `git diff --check`: pass.

## Required Evidence Still Missing

The PostgreSQL API/migration suite cannot create its throwaway databases.
Both the default test admin URL and the local `.env`-derived URL fail with:

`fe_sendauth: no password supplied`

A full `python -m pytest -q` retry on 2026-07-29 confirmed the same environment
blocker during collection of five PostgreSQL-backed modules; no test assertion
ran or failed in those modules.

The following new/affected tests exist but have not executed in this
environment:

- vessel attachment upload/list/tenant-denial/delete API flow;
- cumulative Berth/cargo/PL.03 SOT merge API flow;
- explicit full-revision regression;
- Alembic head upgrade and exactly-one-owner migration assertions;
- full application suite.

Run with a create-database-capable, secret-safe `TEST_ADMIN_DATABASE_URL`:

```powershell
$env:TEST_ADMIN_DATABASE_URL = "<secret PostgreSQL admin URL>"
python -m pytest -q
```

Do not record the URL value in review artifacts or shell output.

## Independent Review Gate

The independent R2 reviewer accepted publication only as a WIP continuation
checkpoint. This is not a PASS disposition and does not authorize FREEZE,
production deployment, or a functional-completion claim.

### Reviewer findings and repair disposition

1. HIGH, RESOLVED AT SOURCE: PL.03 SOT identity, checksum idempotency,
   conflict detection and legacy export dimensions are period-scoped; the
   database uniqueness constraint now includes `reporting_period`.
2. HIGH, RESOLVED AT SOURCE: selecting one conflict no longer narrows
   full-revision supersession; regression coverage expects every active receipt
   in the period to be superseded.
3. MEDIUM, RESOLVED AT SOURCE: attachment database deletion commits
   before storage deletion; failed storage cleanup is returned and audited.
4. MEDIUM, RESOLVED AT SOURCE: scanner/database failures roll back and
   compensate the newly stored upload object.
5. EVIDENCE: PostgreSQL migration, constraints and API flows remain unverified.

Repair evidence: 32 focused tests passed; PostgreSQL DDL, Python compile,
JavaScript syntax and backend unbound-name checks passed.

### Re-review repair

- Initial re-review BLOCKED mutation of already-published Alembic revision
  `x23f0f000023`.
- `x23f0f000023` was restored byte-for-byte to its published Git version.
- New successor `y24f0f000024` carries the period-scoped uniqueness change and
  downgrade refusal when cross-period rows cannot fit the older constraint.
- `STORAGE_DELETE_PENDING` now records the generated storage object key so
  cleanup retry can identify the orphan.
- Alembic reports one head: `y24f0f000024`.
- Independent re-review found no remaining source blocker and accepted the
  repair checkpoint with the PostgreSQL execution limitation.

The reviewer also accepted `frontend/index.html` as necessary UI wiring for
this checkpoint; the work-order amendment records that scope clarification.

## Claim Boundary

This pending review records source and local executable evidence only. It does
not claim production deployment, successful PostgreSQL migration, or live CVF
provider governance.

## 2026-07-30 Vessel Editor Repair Evidence

Status: EXECUTABLE_EVIDENCE_COMPLETE_PENDING_INDEPENDENT_R2_REVIEW

- Direct UI reproduction on imported vessel `AG-15445` proved the vessel save
  stopped with status 422 before the attachment endpoint was called.
- The rejected optional numeric fields were `build_year`, `width_m`,
  `side_height_m`, `draft_m`, `engine_power_cv`,
  `container_capacity_teu`, and `passenger_capacity`; the browser form sent
  each blank as `""`.
- The repair removes blank optional top-level vessel form values after the
  organization payload is preserved and before `POST /api/vessels`.
- `python -m pytest -q tests/test_frontend_ux.py`: 16 passed.
- `node --check frontend/app.js`: pass.
- `git diff --check`: pass.
- Direct Docker PostgreSQL 17 verification on `AG-15445`:
  - vessel save: 200, version advanced to 2;
  - attachment upload: 200, `scan_status=QUARANTINED`;
  - attachment listing: uploaded file present;
  - audit listing: `VESSEL_ATTACHMENT / UPLOAD` present.
- Complete Docker suite with matching PostgreSQL 17 client/server:
  `269 passed`, 3 warnings, 0 failed.
- This evidence closes the prior PostgreSQL execution limitation locally. It
  does not self-approve the new repair; an independent R2 reviewer remains
  required before commit/closure.

### Browser cache follow-up

- Repeated UI attempts still returned 422 because `index.html` retained
  `app.js?v=1.13.1`; the browser reused the pre-repair asset URL.
- The cache key is now `app.js?v=1.13.2`.
- Regression coverage asserts the repaired save logic is loaded through the
  new cache key.
- Targeted frontend suite: 16 passed.
- Fresh live responses verified that the index references `1.13.2` and the
  versioned JavaScript response contains the blank-field normalization.

### Vessel-list attachment indicator

- Both the customer vessel list and the port-register list now show a
  paperclip badge with the attachment count beside the Salan name.
- The helper returns no markup for a zero attachment count, so unattached
  profiles retain the existing row presentation.
- The badge exposes the same Vietnamese count through `title` and
  `aria-label`.
- Frontend cache key advanced to `app.js?v=1.13.3`.
- `python -m pytest -q tests/test_frontend_ux.py`: 17 passed.
- `node --check frontend/app.js`: pass.
- `git diff --check`: pass.
- Fresh live index and JavaScript responses returned 200; the index references
  `1.13.3`, and the served asset contains both indicator integrations.
- Status remains pending independent R2 review; this implementation evidence
  does not authorize commit, push, FREEZE, or production deployment.

#### Visual cache repair

- Operator evidence showed the new SVG rendered with the cached pre-indicator
  stylesheet (`styles.css?v=1.13.1`) and expanded to an unacceptable size.
- The repaired indicator is a plain 14 px paperclip plus count, without a
  badge background or border.
- Explicit SVG dimensions in markup provide a safe presentation before CSS is
  available; CSS and JavaScript are both cache-busted to `1.13.4`.
- Targeted frontend suite: 17 passed. JavaScript syntax and diff checks pass.
- Fresh live responses returned 200 and contain both `1.13.4` asset references,
  the compact CSS rule, and the inline 14 px SVG dimensions.

### Independent UI Repair Review

Reviewer: `/root/independent_ui_repair_review`

Disposition: `PASS_WITH_LIMITATIONS`

No HIGH, MEDIUM, or LOW findings were reported.

The independent reviewer verified:

- blank optional vessel fields are removed before vessel save and attachment
  upload;
- the indicator is absent at zero attachments and present in both list
  renderers;
- accessibility text and 14 px inline/CSS size constraints are present;
- CSS and JavaScript cache keys both use `1.13.4`;
- tenant guards, quarantined storage, and attachment audit behavior remain
  intact.

Independent evidence:

- workspace doctor: 25/25;
- frontend tests: 17/17;
- attachment backend tests: 2/2;
- JavaScript syntax, Python compileall, and diff checks: pass;
- live index/CSS/JavaScript responses: HTTP 200 with expected repair content;
- Docker DB: `AG-15445` has one quarantined attachment and matching
  `VESSEL_ATTACHMENT / UPLOAD` audit attribution;
- full host suite: 268 passed, 2 failures caused solely by unavailable host
  `pg_dump`.

Limitation: no connected browser or Playwright runtime was available for an
independent rendered screenshot/computed-style check. The inline 14 px SVG
dimensions, matching cache-busted stylesheet, and live served-asset evidence
directly mitigate the reported oversized-icon failure.

This is local review evidence only. It does not authorize commit, push,
FREEZE, production deployment, or a live CVF-governance claim.

### Publication Receipt

- Operator authorized commit and pull-request publication after independent
  review.
- Reviewed implementation commit: `31d2da4`.
- Branch:
  `Blackbird081/quanlyxalan:feat/port-staff-declaration-create-import`.
- Pull request: `https://github.com/hoangnmr/quanlyxalan/pull/7`, targeting
  `hoangnmr/quanlyxalan:main`.
- At creation GitHub reported `OPEN`, `MERGEABLE`, with the quality gate in
  progress.
- This receipt does not authorize merge, FREEZE, or production deployment.
