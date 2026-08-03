# Agent Handoff V2

Status: IN_PROGRESS

## Historical Vessel Source-of-Truth Reuse — 2026-07-30

- Operator clarified that Admin-verified or Admin-maintained Salan identity is
  source of truth. A new voyage number is a new call, not a new vessel.
- Continuity drift was reported and the operator authorized reconciliation;
  the stale handoff footer was synchronized to REVIEW/ORCHESTRATOR and the
  workspace doctor passed 25/25.
- Risk: R2 because automatic identity reuse must preserve tenant isolation and
  must not accept conflicting mappings.
- Diagnosis: cumulative filtering correctly retains identical call keys, but
  `_stage_berth` creates every new call's vessel link as `PENDING`; accepted
  vessel identity is stored per import/call and is not reused.
- Phase/role route: REVIEW/ORCHESTRATOR -> INTAKE/ORCHESTRATOR ->
  DESIGN/SPEC_AUTHOR -> SPEC/SPEC_AUTHOR ->
  WORK_ORDER/WORK_ORDER_AUTHOR -> BUILD/IMPLEMENTATION_WORKER.
- Governed artifacts:
  - `docs/decisions/HISTORICAL_VESSEL_SOT_REUSE_DESIGN_20260730.md`
  - `docs/specs/HISTORICAL_VESSEL_SOT_REUSE_SPEC_20260730.md`
  - `docs/work_orders/WO_QLXL_HISTORICAL_VESSEL_SOT_REUSE_20260730.md`
- BUILD acknowledgment: scope is limited to tenant-safe reuse of current
  canonical vessel matches and unambiguous prior Admin-accepted mappings,
  focused tests, and governed truth updates. Production data, schema changes,
  attachment-preview changes, `.claude/`, commit, push, merge, deployment,
  and FREEZE remain outside scope.
- BUILD result:
  - unique exact/normalized matches in the current Salan register are accepted
    automatically;
  - the latest Admin-accepted TOS alias mapping is reused for new voyages and
    a later Admin correction becomes the current SOT;
  - disagreement with the current register remains pending;
  - one manual decision cascades to same-name sibling calls in the import;
  - pre-existing staged previews are repaired by the idempotent reconcile
    endpoint or same-file upload;
  - tenant filtering and call-key incremental merge remain unchanged.
- Executable evidence: SOT unit tests 11/11; focused PostgreSQL API 3/3;
  regression suite 276 passed, 2 backup-tool tests deselected, 2 existing
  openpyxl warnings; compile and diff checks passed.
- Phase/role transition: BUILD/IMPLEMENTATION_WORKER -> REVIEW/REVIEWER.
- Review disposition: `PASS_WITH_LIMITATIONS`; no HIGH, MEDIUM, or LOW finding
  remains. The only limitation is unavailable local `pg_dump` for two
  unrelated backup tests.
- Review artifact:
  `docs/reviews/HISTORICAL_VESSEL_SOT_REUSE_REVIEW_20260730.md`.
- Role handback: REVIEWER -> ORCHESTRATOR. Commit, push, merge, deployment,
  and FREEZE remain unauthorized.
- Operator explicitly requested an independent reviewer before publication and
  authorized commit plus PR creation against the canonical
  `hoangnmr/quanlyxalan` repository.
- Role transition: ORCHESTRATOR -> independent REVIEWER. Publication must wait
  for a PASS disposition. On PASS, COMMIT_STEWARD may commit the exact reviewed
  set, exclude `.claude/`, push the fork branch, and create or update the
  canonical PR. Merge, deployment, and FREEZE remain unauthorized.
- Independent review disposition: `BLOCKED`; the set is not safe to commit or
  publish.
- HIGH accepted finding: `PORT_STAFF` may resolve links, while the SOT query
  reused every accepted link without proving a `PLATFORM_ADMIN` reviewer.
- MEDIUM accepted finding: filtering to accepted links before ordering allowed
  an older acceptance to survive a later Admin rejection.
- No additional finding was reported for attachment preview. Independent
  focused evidence passed 29/29 plus JavaScript syntax, Python compile,
  catalog, diff, and doctor 25/25.
- Phase/role transition: REVIEW/independent REVIEWER ->
  BUILD/REPAIR_WORKER. Repair scope is limited to Admin-authoritative alias
  decisions, latest accepted/rejected semantics, negative tests, continuity,
  and independent re-review. Commit and PR remain blocked pending PASS.
- Repair result:
  - manual alias SOT requires an active `PLATFORM_ADMIN` reviewer;
  - latest Admin decisions are ordered across `ACCEPTED` and `REJECTED`;
  - latest rejection tombstones older acceptance;
  - current-register unique matching remains a separate trusted path;
  - negative tests cover Port Staff exclusion, rejection invalidation, and
    latest Admin correction.
- Repair evidence: combined SOT/frontend 31/31; focused PostgreSQL API 3/3;
  Python/JavaScript syntax and diff checks passed.
- Phase/role transition: BUILD/REPAIR_WORKER -> REVIEW/independent REVIEWER.
  Commit and PR remain blocked pending re-review PASS.
- First re-review remained `BLOCKED` with one HIGH provenance finding:
  Admin-triggered automatic reconciliation stamped the actor as a manual
  reviewer and could therefore seed alias SOT.
- Second repair result:
  - automatic matching/reconciliation leaves reviewer identity and timestamp
    empty;
  - manual resolve always records `MANUAL` with the acting reviewer;
  - an Admin-triggered auto-reconcile regression proves the result cannot seed
    alias SOT after the register match changes.
- Second repair evidence: combined SOT/frontend 32/32; focused PostgreSQL API
  3/3; syntax and diff checks passed.
- The set remains in independent REVIEW and publication remains blocked until
  the same reviewer returns PASS.
- Second independent re-review disposition: `PASS_WITH_LIMITATIONS`; no HIGH,
  MEDIUM, or LOW finding remains.
- Independent evidence: focused 32/32, JavaScript syntax, Python compile,
  catalog, diff, and workspace doctor 25/25 passed.
- Final local repair regression: 279 passed, 2 unrelated backup-tool tests
  deselected, 2 existing openpyxl warnings.
- Reviewer authorized the exact set for commit and PR publication, excluding
  `.claude/`, with post-rebase checks.
- Role transition: independent REVIEWER -> COMMIT_STEWARD under the operator's
  explicit commit/PR authority. Merge, deployment, and FREEZE remain
  unauthorized.

## Vessel Attachment Preview Tranche — 2026-07-30

- Operator requested that selecting a vessel attachment open a preview popup
  instead of downloading immediately; download must be an explicit choice.
- Workspace doctor passed 25/25 before material work.
- Risk: R2 because attachments remain quarantined and preview must preserve
  tenant isolation and browser-content safety.
- Phase/role route: REVIEW/ORCHESTRATOR -> INTAKE/ORCHESTRATOR ->
  DESIGN/SPEC_AUTHOR -> SPEC/SPEC_AUTHOR ->
  WORK_ORDER/WORK_ORDER_AUTHOR -> BUILD/IMPLEMENTATION_WORKER.
- Governed artifacts:
  - `docs/decisions/VESSEL_ATTACHMENT_PREVIEW_DESIGN_20260730.md`
  - `docs/specs/VESSEL_ATTACHMENT_PREVIEW_SPEC_20260730.md`
  - `docs/work_orders/WO_QLXL_VESSEL_ATTACHMENT_PREVIEW_20260730.md`
- BUILD acknowledgment: implementation is limited to an authenticated preview
  dialog, safe image/PDF rendering, explicit download, unsupported Office
  guidance, object-URL cleanup, cache keys, focused tests, browser evidence,
  and governed truth updates. Backend security headers, scanner policy,
  commit, push, merge, deployment, and FREEZE remain outside scope.
- BUILD result:
  - filename selection now opens a dedicated preview dialog;
  - PNG, JPEG, WebP, and PDF use authenticated bytes, with PDF isolated in a
    sandboxed iframe;
  - Word and Excel remain unfetched until the user explicitly downloads;
  - the explicit download action reuses preview bytes where available;
  - object URLs and stale preview requests are cleaned up safely;
  - cache keys advanced together to `1.13.7`.
- Executable evidence: frontend UX 18/18; focused attachment backend 1/1
  against temporary PostgreSQL 17; JavaScript syntax and diff checks passed.
- Full suite evidence: 272 passed and 2 unrelated backup tests failed because
  `pg_dump` is absent from local `PATH`.
- Browser discovery returned no available session, so rendered popup evidence
  remains unavailable.
- Phase/role transition: BUILD/IMPLEMENTATION_WORKER -> REVIEW/REVIEWER.
- Review disposition: `PASS_WITH_LIMITATIONS`; no HIGH, MEDIUM, or LOW finding
  remains in the authorized changed set.
- Review artifact:
  `docs/reviews/VESSEL_ATTACHMENT_PREVIEW_REVIEW_20260730.md`.
- Role handback: REVIEWER -> ORCHESTRATOR. Commit, push, merge, deployment,
  and FREEZE remain unauthorized.

## Admin-only Import/Reports UI Tranche — 2026-07-30

- Operator requested that the `Import dữ liệu` and `Báo cáo hoạt động` tabs be
  visible only to Platform Admin, with all other roles hiding them.
- Operator also requested consistent Vietnamese terminology for the
  user-visible word `Revision`.
- Workspace doctor passed 25/25 before material work.
- Risk: R2 because role-based navigation and direct-route behavior form an
  access-control surface.
- Phase/role transition: REVIEW/ORCHESTRATOR -> INTAKE/ORCHESTRATOR.
- Existing user-owned edits in `frontend/app.js` and `frontend/index.html`
  must be preserved. Untracked `.claude/` remains outside scope.
- Intake boundary: frontend navigation visibility, direct hash-route guard,
  user-visible Vietnamese terminology, focused regression tests, and governed
  continuity/evidence only. Backend report/import authorization, production
  data, deployment, merge, and unrelated UI copy are outside scope.
- Phase/role route: INTAKE/ORCHESTRATOR -> DESIGN/SPEC_AUTHOR ->
  SPEC/SPEC_AUTHOR -> WORK_ORDER/WORK_ORDER_AUTHOR ->
  BUILD/IMPLEMENTATION_WORKER.
- Governed artifacts:
  - `docs/decisions/ADMIN_ONLY_DATA_TABS_DESIGN_20260730.md`
  - `docs/specs/ADMIN_ONLY_DATA_TABS_SPEC_20260730.md`
  - `docs/work_orders/WO_QLXL_ADMIN_ONLY_DATA_TABS_20260730.md`
- BUILD acknowledgment: implementation is limited to the authorized frontend
  navigation, direct hash-route guard, Vietnamese terminology, focused tests,
  and governed truth updates. Existing user-owned edits will be preserved.
  Backend authorization, commit, push, merge, deployment, and FREEZE remain
  unauthorized.
- BUILD result:
  - both navigation links are hidden by default and unhidden only for
    `PLATFORM_ADMIN`;
  - direct non-admin `#import`/`#reports` hashes redirect to `#dashboard` for
    Port Staff or `#declarations` for Customer before page loaders run;
  - user-visible historical import copy consistently uses `Bản sửa đổi`;
  - frontend cache keys advanced together to `1.13.6`;
  - existing user-owned ETB, password, and audit-log copy edits were preserved.
- Executable evidence: frontend UX 18/18; backend static shell 1/1 against
  temporary PostgreSQL 17; JavaScript syntax, diff, catalog, and workspace
  doctor 25/25 passed.
- Phase/role transition: BUILD/IMPLEMENTATION_WORKER -> REVIEW/REVIEWER.
- Review disposition: `PASS_WITH_LIMITATIONS`; no HIGH, MEDIUM, or LOW
  findings. No connected production or rendered multi-role browser session was
  used.
- Review artifact:
  `docs/reviews/ADMIN_ONLY_DATA_TABS_REVIEW_20260730.md`.
- Role handback: REVIEWER -> ORCHESTRATOR. Commit, push, merge, deployment,
  and FREEZE remain unauthorized.
- Operator follow-up authorized a User Guide clarification and one local
  commit. The guide must state that PL.03 from approved LIVE declarations and
  PL.03 reconstructed from confirmed historical/TOS imports are separate
  workflows that share the same output template.
- The operator manually cleaned frontend copy after the first review. Those
  edits are accepted as the intended working version; regression assertions
  must be aligned without reverting the manual copy.
- Phase/role transition: REVIEW/ORCHESTRATOR ->
  BUILD/IMPLEMENTATION_WORKER for the bounded documentation/test repair.
- Publication boundary: one local commit is authorized after review. Push,
  merge, deployment, FREEZE, and untracked `.claude/` remain excluded.
- Documentation repair result: `USER_GUIDE.md` now distinguishes LIVE PL.03
  from historical/TOS PL.03, records their separate sources and overlap rule,
  and reflects Platform Admin-only Import/Reports navigation.
- Focused rerun after preserving the operator's manual copy cleanup:
  18 frontend UX tests passed; JavaScript syntax and diff checks passed.
- Phase/role transition: BUILD/IMPLEMENTATION_WORKER -> REVIEW/REVIEWER.
- Review disposition remains `PASS_WITH_LIMITATIONS`; no new finding was
  introduced by the documentation or copy cleanup.
- Role transition: REVIEWER -> COMMIT_STEWARD under the operator's explicit
  local-commit authority. The exact reviewed tracked set may be committed;
  `.claude/`, push, merge, deployment, and FREEZE remain excluded.
- Local commit completed on `fix/vessel-attachment-download` with message
  `fix: restrict data workflows to admin`; the final commit identifier is
  reported by Git after the continuity receipt is included.
- Role handback: COMMIT_STEWARD -> ORCHESTRATOR. No push was performed.

## Vessel Attachment Access Tranche — 2026-07-30

- The operator reported that the attachment count is visible but cannot be
  clicked to inspect the file.
- Rehydration and workspace doctor passed 25/25.
- Risk: R2 because stored file access must preserve tenant isolation.
- Phase/role route: REVIEW/ORCHESTRATOR -> INTAKE/ORCHESTRATOR ->
  DESIGN/SPEC_AUTHOR -> SPEC/SPEC_AUTHOR ->
  WORK_ORDER/WORK_ORDER_AUTHOR -> BUILD/IMPLEMENTATION_WORKER.
- Authorized work order:
  `docs/work_orders/WO_QLXL_VESSEL_ATTACHMENT_ACCESS_20260730.md`.
- BUILD acknowledgment: implementation is limited to an actionable indicator,
  tenant-guarded forced download, storage read support, cache key, focused
  tests, browser evidence, and governed truth updates. PR #8 remains parked;
  commit, push, merge, deployment, and FREEZE are not authorized.
- BUILD result: both list indicators are buttons; they open/focus the correct
  vessel attachment section; filenames download through a canonical
  vessel-scope guard; response headers force download and prevent sniffing.
- Focused suite: 7 passed. Full Docker PostgreSQL 17 suite: 271 passed,
  3 warnings, 0 failed. Compile, JavaScript syntax, catalog, and diff checks
  passed. A live local request returned the exact PDF bytes and security
  headers.
- Browser skill setup found no available browser session, so rendered click
  evidence is parked without substituting mock proof.
- Phase/role transition: BUILD/IMPLEMENTATION_WORKER ->
  REVIEW/ORCHESTRATOR for independent R2 review.
- Independent disposition: BLOCKED with one MEDIUM and one LOW finding.
- Accepted repair scope: translate MinIO missing-object errors to the endpoint's
  controlled 404 contract; make the download call force blob handling on
  successful responses while preserving JSON error parsing; add regression
  coverage.
- Phase/role return: REVIEW/ORCHESTRATOR -> BUILD/REPAIR_WORKER.
- Repair result: MinIO `NoSuchKey`/`NoSuchObject` now becomes
  `FileNotFoundError` for controlled endpoint 404 behavior; successful
  attachment downloads explicitly request Blob handling while JSON error
  responses remain parseable.
- Post-repair focused suite: 8 passed. Full Docker PostgreSQL 17 suite:
  272 passed, 3 warnings, 0 failed.
- Phase/role transition: BUILD/REPAIR_WORKER -> REVIEW/ORCHESTRATOR for
  independent re-review.
- Independent re-review disposition: PASS_WITH_LIMITATIONS; no remaining
  HIGH, MEDIUM, or LOW findings. Reviewer independently reproduced both MinIO
  missing stages, connection cleanup, JSON-labelled PDF Blob handling, and
  JSON error preservation.
- The only limitation is unavailable rendered-browser evidence. Code is
  complete locally; commit, push, PR, merge, deployment, and FREEZE remain
  outside this request's authority.
- The operator explicitly authorized commit and PR publication for this
  tranche on 2026-07-30. Role transition: ORCHESTRATOR -> COMMIT_STEWARD.
  Publication is limited to `fix/vessel-attachment-download`; user-owned
  `.claude/` remains excluded. Merge, deployment, and FREEZE are not
  authorized.

## Current State

- Project: quanlyxalan
- Tranche: Historical Vessel Source-of-Truth Reuse
- Current mode: REVIEW
- Active phase: REVIEW
- Active role: COMMIT_STEWARD
- Risk: R2
- Next allowed move: commit the exact reviewed set excluding `.claude/`, rebase
  a new publication branch onto `upstream/main`, rerun checks, push the fork,
  and create the canonical PR. Merge, deployment, and FREEZE remain
  unauthorized.
- Parked operator checkpoint: none.

## Intake

- Add file evidence to Salan profiles when Admin supplements data.
- Preserve manually confirmed database facts as SOT across cumulative Berth,
  Salan-detail and PL.03 uploads.
- Restage/reconfirm only completely new facts.

## Governed Artifacts

- Design:
  `docs/decisions/HISTORICAL_SOT_AND_VESSEL_ATTACHMENTS_DESIGN_20260729.md`
- Specification:
  `docs/specs/HISTORICAL_SOT_AND_VESSEL_ATTACHMENTS_SPEC_20260729.md`
- Work order:
  `docs/work_orders/WO_QLXL_SOT_ATTACHMENTS_20260729.md`

## Role And Phase Transitions

- CLOSER/FREEZE -> ORCHESTRATOR/INTAKE: new operator request accepted.
- ORCHESTRATOR -> SPEC_AUTHOR: data ownership and duplicate identities designed.
- SPEC_AUTHOR -> WORK_ORDER_AUTHOR: testable requirements bounded.
- WORK_ORDER_AUTHOR -> IMPLEMENTATION_WORKER: BUILD authorized by the work
  order above.

## Build Acknowledgment

The implementation worker re-read the active continuity surfaces, accepts the
authorized changed set and stop conditions, will preserve tenant isolation and
confirmed SOT data, and will not commit or push without separate authority.

## Build Result

- Source implementation and successor migration complete.
- New SOT/UI unit tests: 20 passed.
- Historical parser/storage tests: 9 passed.
- Combined affected non-PostgreSQL rerun: 29 passed, 1 dependency deprecation
  warning.
- Static checker, compile, app import, JavaScript syntax and diff checks pass.
- Full-suite retry confirmed five PostgreSQL-backed modules remain blocked
  during collection because the local test admin connection has no
  password/CREATE DATABASE authority; no assertion failure was observed.
- Review artifact:
  `docs/reviews/HISTORICAL_SOT_AND_VESSEL_ATTACHMENTS_REVIEW_20260729.md`.
- Role transition: IMPLEMENTATION_WORKER -> ORCHESTRATOR for independent-review
  routing. The implementation worker did not self-approve.

## Operator Continuation Checkpoint

- On 2026-07-29, the operator explicitly accepted deferring the unavailable
  PostgreSQL admin evidence and requested independent review followed by
  commit/push so work can continue on another machine.
- The operator's publication authority applies only to a WIP continuation
  checkpoint. It does not waive independent R2 source review and does not
  authorize FREEZE, production deployment, or a claim that PostgreSQL
  integration passed.
- Independent reviewer assigned: `/root/independent_review`.

## Independent Review Result

- Disposition: `ACCEPT_CHECKPOINT_WITH_LIMITATIONS`.
- Two HIGH findings remain open: PL.03 duplicate identity is not period-scoped;
  full revision can leave overlapping incremental receipts active.
- Two MEDIUM findings remain open: delete is not transactionally safe across
  storage/database; failed upload can leave an orphaned stored object.
- PostgreSQL integration evidence remains parked.
- Role transition: ORCHESTRATOR -> COMMIT_STEWARD after independent review.

## Repair Tranche

- Operator directed that all detected findings be repaired before continuing.
- Phase return: REVIEW -> BUILD.
- Role transition: COMMIT_STEWARD -> REPAIR_WORKER.
- Authorized repair scope is limited to the two HIGH and two MEDIUM findings
  above plus regression tests and governed evidence updates.
- PostgreSQL evidence remains an environment limitation, not a waived
  completion requirement.

## Repair Result

- PL.03 preview now requires an explicit reporting period; SOT retention,
  checksum idempotency, conflict detection and legacy export dimensions are
  period-scoped.
- Historical import uniqueness now includes `reporting_period` and uses
  PostgreSQL `NULLS NOT DISTINCT` to preserve idempotency for undetermined
  periods. Published migration `x23f0f000023` remains immutable; successor
  `y24f0f000024` applies this schema change.
- Full revision validates a selected conflict without narrowing the complete
  conflict set, so all overlapping active receipts are superseded.
- Failed attachment upload rolls back the database and compensates storage.
- Attachment delete commits the database removal before deleting storage and
  reports/audits pending cleanup with the generated object key if storage
  deletion fails.
- Focused regression suite: 32 passed, 1 dependency deprecation warning.
- PostgreSQL DDL compilation, Python compilation, JavaScript syntax and every
  backend unbound-name check passed.
- Phase return: BUILD -> REVIEW.
- Role transition: REPAIR_WORKER -> ORCHESTRATOR for independent re-review.

## Independent Repair Re-review

- Disposition: `ACCEPT_REPAIR_CHECKPOINT_WITH_PG_LIMITATION`.
- No source blocker remains in the four repaired findings.
- Reviewer verified published `x23f0f000023` is byte-identical to the existing
  Git revision and `y24f0f000024` is the single successor head.
- PostgreSQL execution remains parked and is not claimed as passed.
- Role transition: ORCHESTRATOR -> COMMIT_STEWARD.

## UI Repair Continuation — 2026-07-30

- PostgreSQL 17 Docker evidence is now available: the complete application
  suite passed with `268 passed`, including migration, backup and restore.
- Direct UI reproduction on imported vessel `AG-15445` showed three
  `POST /api/vessels` responses with status 422 before any attachment request.
- The reproduced payload sent blank optional numeric controls as empty strings.
  Pydantic rejected `build_year`, `width_m`, `side_height_m`, `draft_m`,
  `engine_power_cv`, `container_capacity_teu`, and `passenger_capacity`.
- Because the vessel save failed before returning `saved.id`, the frontend
  correctly never reached the attachment upload loop; consequently neither an
  attachment row nor `VESSEL_ATTACHMENT/UPLOAD` audit evidence existed.
- Operator explicitly directed repair on 2026-07-30.
- Phase return: REVIEW -> BUILD.
- Role transition: COMMIT_STEWARD -> REPAIR_WORKER.
- BUILD acknowledgment: the repair worker re-read the active continuity
  surfaces and accepts scope limited to frontend blank optional-field
  normalization, regression coverage, and executable save/upload/audit
  verification. No commit or push is authorized by this instruction.
- Repair result: `saveVessel()` now removes blank optional form values after
  preserving the nested organization payload and before the vessel API call.
- Regression coverage verifies normalization occurs before save and before the
  attachment upload loop.
- Targeted frontend tests: `16 passed`; JavaScript syntax and `git diff
  --check`: pass.
- Direct Docker PostgreSQL reproduction on imported vessel `AG-15445`:
  vessel update returned 200/version 2; attachment upload returned 200 with
  `QUARANTINED`; attachment listing returned the uploaded file; audit listing
  returned `VESSEL_ATTACHMENT / UPLOAD`.
- Full Docker PostgreSQL 17 suite after repair: `269 passed`, 3 dependency/data
  validation warnings, 0 failed.
- Phase return: BUILD -> REVIEW.
- Role transition: REPAIR_WORKER -> ORCHESTRATOR for independent R2 review
  routing. The repair worker has not self-approved or authorized commit/push.
- Follow-up UI reproduction still returned 422 because `index.html` retained
  the pre-repair `app.js?v=1.13.1` cache key; the server asset contained the
  fix, but the browser reused the old URL after a 304 page response.
- Operator reported the repeated failure and continued repair authority.
- Phase return: REVIEW -> BUILD.
- Role transition: ORCHESTRATOR -> REPAIR_WORKER.
- BUILD acknowledgment: scope is limited to cache-busting the repaired
  JavaScript asset, regression coverage, and served-asset verification.
- Cache key advanced from `app.js?v=1.13.1` to `app.js?v=1.13.2`.
- Regression coverage binds the vessel blank-field repair to the new cache key.
- Targeted frontend tests: `16 passed`; JavaScript syntax and diff checks pass.
- Live server verification: fresh index response references `1.13.2`; the
  `app.js?v=1.13.2` response contains the blank-field normalization repair.
- Phase return: BUILD -> REVIEW.
- Role transition: REPAIR_WORKER -> ORCHESTRATOR for independent R2 review.
- Independent reviewer: `/root/independent_ui_repair_review`.
- Disposition: `PASS_WITH_LIMITATIONS`; no HIGH, MEDIUM, or LOW findings.
- Reviewer independently verified canonical date boundaries, unchanged
  customer/reporting-unit scope, scoped-column projection, regression cleanup,
  2 focused PostgreSQL tests, existing RBAC coverage, helper assertions,
  compile/diff checks, and workspace doctor 25/25.
- Limitation: full GitHub quality-gate rerun remains pending after publication;
  reporting-unit warning aggregation was source/RBAC reviewed rather than
  covered by a second warning-specific test.
- Role transition: ORCHESTRATOR -> COMMIT_STEWARD under the operator's
  standing PR completion authority.
- During publication, canonical owner merged PR #7 at merge commit `123bfa8`
  while the warning repair was being prepared; PR #7 can no longer receive
  new commits.
- Created clean follow-up branch `fix/dashboard-certificate-warning-count`
  from `upstream/main` and cherry-picked only the independently accepted repair
  as `76c7f12`. The follow-up diff contains six bounded files and no prior PR
  history.
- Follow-up PR: `https://github.com/hoangnmr/quanlyxalan/pull/8`.
- GitHub quality-gate run `30515776754`: SUCCESS — 272 passed, 3 warnings,
  0 failed; PostgreSQL client check, compile, diff check, and secret guard all
  passed.
- GitHub reports PR #8 `OPEN`, `CLEAN`, and `MERGEABLE`.
- Role transition: COMMIT_STEWARD -> ORCHESTRATOR after publication handback.
- Merge and FREEZE remain unauthorized.
- Independent reviewer: `/root/independent_ui_repair_review`.
- Independent disposition: `PASS_WITH_LIMITATIONS`; no HIGH, MEDIUM, or LOW
  findings.
- Reviewer reproduced the PGDG install in clean Ubuntu 24.04 and confirmed
  `pg_dump 17.10`, verified YAML parsing, the `GITHUB_PATH` handoff, 18 focused
  tests, compile/diff/secret checks, and workspace doctor 25/25.
- The only limitation is that the repaired workflow has not yet been
  pushed/rerun on GitHub; the static contract test is supplemented by the
  clean-container reproduction.
- Role transition: ORCHESTRATOR -> COMMIT_STEWARD under the operator's PR
  completion authority.
- CI repair commit: `57b8bc6` (`ci: align PostgreSQL client with test
  service`), pushed to the PR head branch.
- GitHub Actions run `30509548693`: SUCCESS.
- Full GitHub evidence: 271 passed, 3 warnings, 0 failed; PostgreSQL client
  install/version check, Python compile, diff check, and secret guard all
  passed.
- PR body now records both migrations, downgrade refusal conditions,
  deployment command, corrected CI failure cause, independent review,
  limitations, and the successful quality-gate receipt.
- GitHub rejected formal reviewer/assignee/label mutation from the fork
  account because it lacks canonical-repository permission. This is a
  repository-authorization limitation, not missing code or evidence.
- Role transition: COMMIT_STEWARD -> ORCHESTRATOR after code-complete
  publication handback.
- Merge and FREEZE remain unauthorized.
- Operator requested a visible icon when a Salan profile already has one or
  more attachments.
- Phase return: REVIEW -> BUILD.
- Role transition: ORCHESTRATOR -> IMPLEMENTATION_WORKER.
- BUILD acknowledgment: scope is limited to the existing vessel-list and
  port-register row renderers, attachment-indicator presentation, frontend
  cache key, regression tests, and governed evidence synchronization.
- Both vessel list renderers now place a paperclip badge and attachment count
  beside the Salan name when `attachments.length > 0`; rows without attachments
  render no indicator.
- The indicator includes matching title and accessible-label text such as
  `1 file đính kèm`.
- Frontend cache key advanced from `app.js?v=1.13.2` to `1.13.3`.
- Targeted frontend suite: `17 passed`; JavaScript syntax and diff checks pass.
- Live server responses returned 200, referenced `1.13.3`, contained the
  indicator helper, and contained both list integrations.
- Phase return: BUILD -> REVIEW.
- Role transition: IMPLEMENTATION_WORKER -> ORCHESTRATOR for independent R2
  review. No commit or push is authorized by this operator instruction.
- Operator visual feedback showed the JavaScript `1.13.3` indicator rendered
  against cached `styles.css?v=1.13.1`, leaving the paperclip SVG unconstrained
  and oversized.
- Phase return: REVIEW -> BUILD; role transition: ORCHESTRATOR ->
  REPAIR_WORKER for the bounded visual repair.
- The indicator is now a plain compact 14 px icon and count without the pill
  background/border. SVG width and height are also present in the markup so a
  stale stylesheet cannot enlarge it again.
- Both stylesheet and JavaScript cache keys advanced to `1.13.4`.
- Targeted frontend suite remains `17 passed`; syntax, diff, and live served
  asset checks pass.
- Phase return: BUILD -> REVIEW; role transition: REPAIR_WORKER ->
  ORCHESTRATOR. No commit or push is authorized.
- Continuity drift identified on 2026-07-30: the active-state pointer was
  `REVIEW / ORCHESTRATOR`, while this handoff's summary header still described
  the earlier `BUILD / IMPLEMENTATION_WORKER` checkpoint.
- Operator explicitly authorized reconciliation and independent review. The
  header is synchronized to `REVIEW / ORCHESTRATOR`; the detailed transition
  history above remains unchanged.

## Independent UI Repair Review — 2026-07-30

- Independent reviewer: `/root/independent_ui_repair_review`.
- Reviewer role was isolated from the implementation worker; the reviewer
  performed read-only inspection and made no source or governance edits.
- Disposition: `PASS_WITH_LIMITATIONS`.
- Findings: none at HIGH, MEDIUM, or LOW severity.
- Verified the blank optional-value normalization ordering, both attachment
  indicator integrations, zero-count suppression, accessible title/label,
  inline and CSS 14 px constraints, matching `1.13.4` CSS/JavaScript cache
  keys, tenant guards, quarantine behavior, and audit flow.
- Independent executable evidence:
  - workspace doctor: 25/25;
  - frontend tests: 17/17;
  - attachment backend tests: 2/2;
  - JavaScript syntax, Python compileall, and diff checks: pass;
  - live index/CSS/JavaScript assets: HTTP 200 with the expected `1.13.4`
    references and compact indicator rules;
  - Docker DB: `AG-15445` has one quarantined attachment and a corresponding
    `VESSEL_ATTACHMENT / UPLOAD` audit with organization/reporting-unit
    attribution.
- Full host suite: 268 passed, 2 environment-only failures because host
  `pg_dump` is unavailable; neither failure touches the reviewed changes.
- Limitation: no connected browser or Playwright runtime was available for an
  independent rendered screenshot/computed-style check. Source constraints
  and live asset checks directly cover the oversized-SVG regression.
- Claim boundary: local Docker/test/runtime evidence only; no production,
  deployment, or live CVF-governance claim.
- Active role remains ORCHESTRATOR after reviewer handback. Commit, push, and
  FREEZE remain unauthorized pending operator direction.
- Operator authorized commit and PR creation targeting the canonical
  `hoangnmr/quanlyxalan` repository.
- Role transition: ORCHESTRATOR -> COMMIT_STEWARD.
- Commit scope is limited to the eight tracked reviewed files. User-owned
  untracked `.claude/` remains excluded. Publication must use the
  `Blackbird081` fork branch and target `hoangnmr/quanlyxalan:main`; the
  COMMIT_STEWARD must detect and update an existing PR instead of creating a
  duplicate.

## Commit And PR Receipt — 2026-07-30

- Reviewed changed-set commit: `31d2da4` (`fix: complete vessel attachment UI
  workflow`).
- Pushed branch:
  `Blackbird081/quanlyxalan:feat/port-staff-declaration-create-import`.
- Canonical target: `hoangnmr/quanlyxalan:main`.
- Pull request: `https://github.com/hoangnmr/quanlyxalan/pull/7`.
- Duplicate-PR check returned no existing PR for this head before creation.
- GitHub reported the PR as `OPEN` and `MERGEABLE`; quality gate was running
  when the receipt was written.
- User-owned untracked `.claude/` was not staged, committed, or pushed.
- Role transition: COMMIT_STEWARD -> ORCHESTRATOR after publication handback.
- Merge and FREEZE remain outside this authorization.

## PR Quality-Gate Repair — 2026-07-30

- Operator directed completion of PR #7 after the readiness audit found a
  failed quality gate.
- GitHub evidence: 268 tests passed and two backup tests failed because the CI
  service ran PostgreSQL 17.10 while the runner resolved `pg_dump` 16.14.
- The PR body incorrectly generalized this CI failure as a missing `pg_dump`;
  it must be corrected to distinguish the local missing-client limitation from
  the CI version mismatch.
- Phase return: REVIEW -> BUILD.
- Role transition: ORCHESTRATOR -> REPAIR_WORKER.
- BUILD acknowledgment: repair is limited to PostgreSQL client alignment in
  `.github/workflows/ci.yml`, a focused CI configuration regression test,
  complete PR metadata, executable checks, continuity evidence, and CI
  monitoring. Merge and FREEZE are not authorized.
- Repair result: the workflow installs `postgresql-client-17`, prepends its
  binary directory through `GITHUB_PATH`, and verifies `pg_dump` major version
  17 before dependency installation and pytest.
- Added `tests/test_ci_config.py` to lock the PostgreSQL 17 service/client/path
  contract.
- Focused CI/frontend suite: 18 passed. Alembic reports one head
  (`y24f0f000024`); Python compile, JavaScript syntax, diff, catalog, and
  workspace doctor checks pass.
- Phase return: BUILD -> REVIEW.
- Role transition: REPAIR_WORKER -> ORCHESTRATOR for independent R2 review.

## Claim Boundary

This tranche changes application data/storage behavior. It does not claim live
AI governance behavior.

## Vessel Attachment Access PR Receipt — 2026-07-30

- Initial reviewed commit: `dbdeae2`.
- Canonical `main` advanced when PR #8 was merged at `adafe65`; PR #9 initially
  reported a conflict.
- Rebased onto `adafe65`, resolved continuity conflicts by preserving both the
  merged dashboard-warning receipts and the attachment-access tranche, then
  reran 9 focused tests successfully.
- Final reviewed source commit after rebase: `807e9d9`.
- Pushed with `--force-with-lease` to
  `Blackbird081/quanlyxalan:fix/vessel-attachment-download`.
- Pull request: `https://github.com/hoangnmr/quanlyxalan/pull/9`.
- GitHub quality gate `30517459808`: SUCCESS — 273 passed, 3 warnings,
  0 failed; PostgreSQL 17 client check, compile, diff check, and secret guard
  passed.
- GitHub reports PR #9 `OPEN`, `CLEAN`, and `MERGEABLE`.
- User-owned `.claude/` was not staged, committed, or pushed.
- Role transition: COMMIT_STEWARD -> ORCHESTRATOR after publication handback.
- Merge and FREEZE remain unauthorized.

## Dashboard Certificate Warning Repair — 2026-07-30

- Operator production screenshot showed 105 vessels and 104 certificate
  warnings while the vessel list showed nearly every dated certificate as
  valid.
- Source diagnosis: `/api/dashboard` counted every vessel whose
  `certificate_expiry_date` was non-null; the detailed list correctly used
  `certificate_status()` and therefore disagreed with the dashboard.
- The observed numbers match the defect exactly: 104 dated profiles were
  counted and the single undated profile was excluded.
- Phase return: REVIEW -> BUILD.
- Role transition: ORCHESTRATOR -> REPAIR_WORKER.
- BUILD acknowledgment: scope is limited to dashboard warning aggregation in
  `backend/app.py`, tenant-scoped regression coverage in
  `tests/test_backend.py`, governed evidence, PR publication, and CI
  monitoring. Production data will not be changed. Merge and FREEZE are not
  authorized.
- Repair result: dashboard aggregation now projects only scoped certificate
  values and classifies each with the same canonical `certificate_status()`
  helper used by vessel rows; only `EXPIRING`/`EXPIRED` count.
- Regression coverage adds valid (31 days), expiring (30 days), expired, null,
  malformed, and out-of-scope cases. The expected warning delta is exactly 2.
- Docker PostgreSQL 17 focused evidence: 2 passed.
- Python compile and diff check: pass.
- Phase return: BUILD -> REVIEW.
- Role transition: REPAIR_WORKER -> ORCHESTRATOR for independent R2 review.

## Vessel Preview and Historical Vessel SOT Publication — 2026-07-30

- Independent review initially blocked publication because Port Staff decisions
  could seed alias truth, a later Admin rejection did not tombstone an older
  acceptance, and automated reconciliation could appear to carry a manual
  reviewer identity.
- Repairs restrict reusable alias truth to the latest active Platform Admin
  decision, honor later Admin rejection, and leave automated review provenance
  empty while preserving explicit manual reviewer attribution.
- The same independent reviewer returned `PASS_WITH_LIMITATIONS` with no open
  HIGH, MEDIUM, or LOW findings. Limitations are the unavailable rendered
  browser preview and the local absence of `pg_dump`.
- Reviewed source commit after rebasing onto `upstream/main`: `77bb8d8`
  (`fix: preview attachments and reuse verified vessel identity`).
- Post-rebase evidence: 32 focused tests passed; Python and JavaScript syntax,
  diff, catalog, and workspace doctor 25/25 checks passed.
- Earlier full PostgreSQL 17 regression evidence: 279 passed and 2 backup tests
  deselected solely because local `pg_dump` is unavailable.
- User-owned untracked `.claude/` remains excluded from staging and commits.
- Next governed move: push
  `Blackbird081/quanlyxalan:fix/vessel-preview-sot-reuse`, create a PR against
  `hoangnmr/quanlyxalan:main`, monitor the quality gate, and record the
  publication receipt.
- Merge, deployment, and FREEZE remain unauthorized.

## Vessel Preview and Historical Vessel SOT PR Receipt — 2026-07-30

- Pushed branch:
  `Blackbird081/quanlyxalan:fix/vessel-preview-sot-reuse`.
- Canonical pull request:
  `https://github.com/hoangnmr/quanlyxalan/pull/10`.
- GitHub reported the PR as `OPEN` and `MERGEABLE`.
- Quality gate `30558812593`: SUCCESS — PostgreSQL client 17.10 verified,
  281 tests passed with 3 warnings and 0 failures; compile, diff check, and
  secret guard passed.
- User-owned untracked `.claude/` was not staged, committed, or pushed.
- Role transition: COMMIT_STEWARD -> ORCHESTRATOR after publication handback.
- Next governed move belongs to the canonical owner: review PR #10 and decide
  whether to merge.
- Merge, deployment, and FREEZE remain unauthorized in this session.

## Historical Snapshot, Per-Call PL.03 And Berth Analytics — 2026-08-02

- Operator authorized Platform Admin cleanup of obsolete historical receipts,
  cumulative-snapshot replacement, one PL.03 row per Salan voyage/timeline,
  and Activity Report filtering by Berth column H.
- Clarification: Berth code is not a PL.03 column; it is an Activity Report
  filter dimension.
- Risk: R2 because receipt deletion and snapshot activation affect retained
  report facts and must preserve tenant isolation.
- Phase/role route: REVIEW/ORCHESTRATOR -> INTAKE/ORCHESTRATOR ->
  DESIGN/SPEC_AUTHOR -> SPEC/SPEC_AUTHOR ->
  WORK_ORDER/WORK_ORDER_AUTHOR -> BUILD/IMPLEMENTATION_WORKER.
- Governed artifacts:
  - `docs/decisions/HISTORICAL_SNAPSHOT_CALL_ROWS_BERTH_FILTER_DESIGN_20260802.md`
  - `docs/specs/HISTORICAL_SNAPSHOT_CALL_ROWS_BERTH_FILTER_SPEC_20260802.md`
  - `docs/work_orders/WO_QLXL_HISTORICAL_SNAPSHOT_CALL_BERTH_20260802.md`
- BUILD acknowledgment: implementation is limited to safe deletion of
  non-active receipts, cumulative-versus-partial classification, per-call
  historical PL.03 rows, berth-filtered analytics/export, focused tests and
  governed truth updates. No production receipt or source archive will be
  deleted during verification. Commit, push, merge, deployment and FREEZE
  remain unauthorized.

## Historical Snapshot Tranche Review — 2026-08-02

- BUILD result: cumulative snapshots replace the relevant active snapshot;
  partial workbooks stage only new facts; Platform Admin can delete inactive
  history; historical PL.03 writes one row per Berth call; Activity Reports
  and their Excel export filter by berth without adding berth to PL.03.
- Role/phase transition: IMPLEMENTATION_WORKER/BUILD -> REVIEWER/REVIEW.
- Review found one MEDIUM API-contract defect: a direct client could request
  incremental merge for a cumulative snapshot. The backend now rejects that
  combination with 409, and tests cover both invalid action directions.
- Re-review disposition: PASS_WITH_LIMITATIONS; no open HIGH, MEDIUM or LOW
  finding remains.
- Evidence: PostgreSQL 17 regression 280 passed, 2 unrelated backup tests
  deselected; frontend 18 passed; compile, JavaScript syntax, unbound-name,
  diff and focused XLSX/API checks passed.
- Limitations: no rendered browser session; local host lacks `pg_dump`; no
  production data or source archive was removed.
- Role transition: REVIEWER -> ORCHESTRATOR for operator handback.
- Next move requires new authorization for commit/push/PR, production cleanup,
  deployment or FREEZE.

## PL Report Source Integration — 2026-08-02

- Operator approved integrating historical/TOS data into the Activity Report
  export area with an explicit requirement to keep the UI clear for end users.
- Current truth: the three report cards read approved LIVE declarations; TOS
  facts are available only in analytics and the separate historical PL.03
  shortcut.
- Risk: R2 because combined reporting must not duplicate overlapping LIVE and
  historical periods or convert unavailable historical metrics into zero.
- Phase/role route: REVIEW/ORCHESTRATOR -> INTAKE/ORCHESTRATOR ->
  DESIGN/SPEC_AUTHOR -> SPEC/SPEC_AUTHOR ->
  WORK_ORDER/WORK_ORDER_AUTHOR -> BUILD/IMPLEMENTATION_WORKER.
- Governed artifacts:
  - `docs/decisions/REPORT_EXPORT_SOURCE_INTEGRATION_DESIGN_20260802.md`
  - `docs/specs/REPORT_EXPORT_SOURCE_INTEGRATION_SPEC_20260802.md`
  - `docs/work_orders/WO_QLXL_REPORT_EXPORT_SOURCE_INTEGRATION_20260802.md`
- BUILD acknowledgment: implementation is limited to source-aware PL.02 and
  PL.03 exports, explicit LIVE-only PL.01 presentation, overlap protection,
  compact source UX, executable tests and governed truth updates. Existing
  uncommitted tranche changes remain preserved. Production changes, commit,
  push, deployment and FREEZE remain unauthorized.

## PL Report Source Integration Review — 2026-08-02

- BUILD result: PL.01 stays LIVE; PL.02 and PL.03 export from LIVE,
  historical/TOS or non-overlapping combined sources through one compact
  selector. Unsupported historical metrics remain blank.
- Role/phase transition: IMPLEMENTATION_WORKER/BUILD -> REVIEWER/REVIEW.
- Review repaired three findings: combined PL.03 now permits a LIVE-only
  range, combined PL.03 rows are chronologically sorted, and the fixed LIVE
  badge uses a valid theme token.
- Re-review disposition: PASS_WITH_LIMITATIONS; no open HIGH, MEDIUM or LOW
  finding remains.
- Evidence: PostgreSQL 17 regression 281 passed, 2 unrelated backup tests
  deselected; frontend 19 passed; compile, JavaScript syntax, unbound-name and
  diff checks passed; governed catalog passed and workspace doctor passed
  25/25.
- Browser discovery returned no available session, so rendered visual evidence
  remains unavailable. No production data was changed.
- Role transition: REVIEWER -> ORCHESTRATOR for operator handback.
- Next move requires explicit authorization for commit/push/PR, production
  rollout or FREEZE.

## PL Report Source Evidence Publication Repair — 2026-08-03

- Operator explicitly authorized commit and PR creation targeting
  `hoangnmr/quanlyxalan:main`. Merge, deployment and FREEZE remain
  unauthorized; user-owned `.claude/` remains excluded.
- Independent read-only evidence review accepted two publication blockers:
  the seed script must validate the admin connection that executes the
  destructive reset, and the executable receipt must verify combined PL.02
  independently from combined PL.03.
- Additional evidence hygiene scope: align log names/statuses, remove sample
  credentials, record reproducible command/version metadata, correct mobile
  evidence claim boundaries, synchronize the User Guide, catalog and
  implementation truth, and preserve the unavailable-browser limitation.
- Phase/role transition: REVIEW/REVIEWER -> BUILD/REPAIR_WORKER.
- BUILD acknowledgment: changes are limited to the accepted evidence,
  documentation, continuity and test repairs plus the already authorized
  report-source implementation set. No production data reset, merge,
  deployment or FREEZE is authorized.
- Repair result: both destructive database connections are constrained to
  local hosts and named databases; PL.02 and PL.03 combined success/overlap
  have separate XLSX/log receipts; obsolete ambiguous artifacts were removed;
  local PostgreSQL evidence is accurately labelled 16.11 while PostgreSQL 17
  remains a separate regression claim; User Guide, catalog and implementation
  truth are synchronized.
- Independent browser discovery returned no available session. Existing local
  Chromium screenshots are retained, but the report now marks the dedicated
  mobile annex selector as not directly captured rather than substituting mock
  evidence.
- Review evidence: report verifier passed PL.01 LIVE/422, historical PL.02,
  per-call historical PL.03, combined PL.02/PL.03 and both 409 overlap guards;
  five seed safety rejection cases passed; frontend 19/19; application suite
  281 passed with two backup-only environment failures because `pg_dump` is
  absent; compile, JavaScript syntax, unbound-name, catalog, JSON, relative
  links, XLSX package, secret and diff checks passed.
- Review disposition: `PASS_WITH_LIMITATIONS`; no open HIGH, MEDIUM or LOW
  finding remains. Limitations are the unavailable new browser frame and the
  local missing `pg_dump`; the PR quality gate owns the PostgreSQL 17 client
  rerun.
- Phase/role transition: BUILD/REPAIR_WORKER -> REVIEW/REVIEWER ->
  REVIEW/COMMIT_STEWARD under the operator's explicit commit and PR authority.
- Publication scope is the exact reviewed historical snapshot and PL report
  source integration changed set, including evidence and governed truth;
  `.claude/` is excluded. Merge, deployment and FREEZE remain unauthorized.

## Historical Snapshot And Report Source PR Receipt — 2026-08-03

- Reviewed commit after rebasing onto `upstream/main`:
  `287427d592ffc552312ea4a0db5887eae3be957f` (`feat: integrate historical
  TOS report sources`).
- Post-rebase evidence: focused backend 12/12; frontend 19/19; Python compile,
  JavaScript syntax, unbound-name, catalog, diff and secret-pattern checks
  passed; workspace doctor passed 25/25.
- Pushed fork branch:
  `Blackbird081/quanlyxalan:feat/historical-report-source-integration`.
- Canonical pull request: `https://github.com/hoangnmr/quanlyxalan/pull/11`.
- GitHub reported the PR `OPEN` and `MERGEABLE`; quality gate run
  `30779036098` was in progress when this receipt was written.
- User-owned `.claude/` was not staged, committed or pushed.
- Role transition: COMMIT_STEWARD -> ORCHESTRATOR after publication handback.
  The canonical owner owns merge disposition. Production cleanup, deployment
  and FREEZE remain unauthorized.
