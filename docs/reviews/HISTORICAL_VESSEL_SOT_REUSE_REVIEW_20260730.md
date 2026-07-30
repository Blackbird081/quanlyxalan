# Historical Vessel Source-of-Truth Reuse Review

Review ID: REVIEW-QLXL-HISTORICAL-VESSEL-SOT-REUSE-20260730

Work order: WO-QLXL-HISTORICAL-VESSEL-SOT-REUSE-20260730

Disposition: PASS_WITH_LIMITATIONS

Risk: R2

## Scope Review

- Berth call identity remains vessel name + year + voyage; a new voyage remains
  a new operational call.
- Vessel identity is reconciled separately from the call key.
- A unique exact or normalized current-register match is accepted
  automatically.
- The latest Admin-accepted TOS alias mapping is reused when its candidate
  remains assigned to the current reporting unit.
- A newer Admin correction becomes the current mapping.
- Disagreement between accepted history and a unique current-register match
  remains pending.
- One manual acceptance cascades to pending sibling rows with the same
  normalized TOS name in the same import.
- Already-staged previews are repaired idempotently when the historical
  reconcile endpoint runs or the same file is uploaded again.
- Candidate selection remains tenant-scoped.

## Executable Evidence

- `tests/test_sot_merge_unit.py`: 11 passed.
- Focused PostgreSQL 17 API scenarios: 3 passed.
- Regression suite excluding two local backup-tool tests: 276 passed,
  2 deselected, 2 existing openpyxl warnings.
- Python compile and `git diff --check`: passed.

## Independent Findings

- HIGH: `PORT_STAFF` may resolve a manual link, but the SOT query treated every
  accepted manual link as Admin authority. Repair must require an active
  `PLATFORM_ADMIN` reviewer before a manual alias can seed reusable SOT.
- MEDIUM: the query selected only accepted rows before ordering decisions, so
  a later Admin rejection could not invalidate an older accepted alias.
  Repair must select the latest Admin decision across accepted and rejected
  states, then reuse only an accepted latest decision.

Publication is blocked until both findings are repaired and independently
re-reviewed with negative coverage.

## Repair Submitted For Re-review

- Manual alias SOT now joins the reviewer account and accepts decisions only
  from an active `PLATFORM_ADMIN`.
- The latest Admin decision is selected across both `ACCEPTED` and `REJECTED`;
  rejection produces a tombstone and prevents older mapping reuse.
- Unique current-register matching remains an independent trusted path.
- Negative tests cover Port Staff exclusion, accepted-to-rejected invalidation,
  and latest Admin correction.
- Repair evidence: combined SOT/frontend tests 31/31; focused PostgreSQL API
  scenarios 3/3; Python and JavaScript syntax plus diff checks passed.

Disposition remains blocked until independent re-review.

## Second Repair Submitted For Re-review

- Auto-match and auto-reconcile no longer write reviewer identity or review
  timestamp.
- The manual resolve endpoint always records `MANUAL` provenance with the
  acting reviewer.
- Legacy manual decisions remain recognizable through their non-null reviewer,
  while automatic decisions remain excluded from the Admin-only SOT join.
- New regression proves that an Admin-triggered automatic reconciliation does
  not become alias SOT after the unique register match later disappears.
- Evidence: combined SOT/frontend tests 32/32 and focused PostgreSQL API 3/3.

## Independent Re-review

- Final disposition: `PASS_WITH_LIMITATIONS`.
- The same independent reviewer verified both original findings and the
  automatic-provenance follow-up are resolved.
- No HIGH, MEDIUM, or LOW finding remains.
- Independent evidence: 32/32 focused tests, JavaScript syntax, Python compile,
  catalog, diff, and workspace doctor 25/25 passed.
- Final local regression after repair: 279 passed, 2 backup-tool tests
  deselected, 2 existing openpyxl warnings.
- The exact reviewed set is safe to commit and publish as a PR, excluding
  `.claude/`, with post-rebase checks required.

## Limitations

Two backup tests were excluded because local `pg_dump` is not installed in
`PATH`; both are unrelated to historical import reconciliation. No production
data was modified or used as evidence.

## Claim Boundary

This review covers local historical-import and tenant-isolation behavior only.
It makes no live AI-governance claim.
