# Historical SOT And Vessel Attachments Specification

Spec ID: SPEC-QLXL-SOT-ATTACHMENTS-20260729

Status: AUTHORIZED_SCOPE

Phase: SPEC

Risk: R2

## Functional Requirements

### FR-1 Vessel attachment ownership

An attachment must belong to exactly one declaration or vessel. Existing
declaration attachments remain readable after migration.

### FR-2 Vessel attachment API

Authorized users in vessel scope can list and upload vessel attachments.
Upload must reuse the existing file validation, quarantine/scanner and checksum
controls. Deletion must remove both the database row and stored object only
after tenant authorization.

### FR-3 Vessel editor

The Salan/vessel modal shows current attachments and a multiple-file input for
new evidence. Saving a new or edited vessel uploads selected files to that
vessel and refreshes the displayed profile.

### FR-4 Confirmed SOT retention

Previewing cumulative Berth, cargo-detail or reported PL.03 files must compare
against active confirmed imports in the same reporting unit. Repeated SOT rows
must not be restaged and must not lose their existing validation or reviewed
vessel-link decisions.

### FR-5 New-row confirmation

Only rows not represented by the confirmed SOT are stored in the preview
import and included in its accepted/review/rejected counts. The response and
mapping receipt expose `sotRetainedCount` and `newRowCount`.

### FR-6 Incremental merge

When a preview contains new rows alongside retained SOT rows, confirmation with
`MERGE_NEW_RECORDS` activates the new import without superseding prior active
imports. A missing conflict action remains a conflict response when an active
same-scope import exists.

### FR-7 Explicit correction

`ACTIVATE_NEW_REVISION` remains an explicit, reason-required correction path.
It may supersede active same-scope imports. Cumulative upload alone must never
select this path automatically.

### FR-8 Report composition

Historical PL.03 export composes all active incremental Berth, cargo-detail and
reported-PL.03 receipts for the selected reporting unit/period, without
duplicating retained SOT rows.

## Security And Integrity Requirements

- Vessel attachment operations must call the canonical vessel-scope guard.
- Filenames are metadata only; stored names are generated server-side.
- Raw secrets and attachment bytes must not enter audit text.
- Duplicate matching must remain tenant-scoped.
- Cargo duplicate matching must preserve multiplicity.

## Validation Requirements

- Alembic upgrade/downgrade test or executable migration inspection.
- Targeted `pytest` for historical imports, vessel endpoints, attachment
  storage, and frontend contracts.
- `python -m compileall -q backend`.
- Full suite.
- `git diff --check`.

## Non-Goals

- No automatic overwrite of confirmed facts.
- No automatic merge of changed values into an existing business identity.
- No external object-storage provider integration.
- No change to declaration attachment UX.
- No commit, push, deployment, or live CVF governance claim.

## Stop Conditions

Stop BUILD if duplicate identity cannot be established without silently
collapsing valid facts, if a migration would orphan an existing declaration
attachment, or if tenant tests expose cross-unit file/data access.
