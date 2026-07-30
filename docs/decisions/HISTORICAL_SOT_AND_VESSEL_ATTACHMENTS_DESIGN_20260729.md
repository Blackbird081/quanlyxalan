# Historical SOT And Vessel Attachments Design

Decision ID: ADR-QLXL-SOT-ATTACHMENTS-20260729

Status: APPROVED_BY_OPERATOR_SCOPE

Phase: DESIGN

Risk: R2

## Intent

Support documentary evidence on a manually maintained Salan profile and make
confirmed database facts the source of truth when cumulative TOS workbooks are
uploaded again with additional vessels.

## Source-Of-Truth Decision

An active, confirmed historical row remains authoritative. A later cumulative
workbook must not replace that row merely because it repeats the same business
identity. Preview classifies rows into:

- `SOT_EXISTING`: already represented by active confirmed data; retain the
  database row and do not ask the operator to confirm it again;
- `NEW`: not represented in active confirmed data; stage it in the new import
  and apply the existing validation/review flow.

Explicit correction remains a separate revision action. It is never inferred
from a cumulative file.

## Duplicate Identity

- Berth row: normalized vessel/year/voyage call key.
- PL.03 row: normalized registration number, falling back to normalized vessel
  name when registration is blank.
- Cargo-detail row: a normalized fact fingerprint over call key, container
  size, full/empty state, trade scope, movement method, direction, weight state
  and weight value. Matching uses multiset counts so legitimately repeated,
  identical cargo facts are not collapsed.

Only active imports (`COMMITTED` or `REVIEW`) participate in SOT matching.
Rejected and superseded imports do not.

## Incremental Import Decision

The new import stores only `NEW` rows. Its mapping receipt records the number
of retained SOT rows and newly staged rows. If the file contains additions, the
operator confirms an incremental merge; prior imports remain active and the
new import becomes another active receipt. If there are no additions, keeping
the existing data rejects the empty preview without changing the SOT.

The existing explicit `ACTIVATE_NEW_REVISION` path remains available for a
deliberate correction with a mandatory reason.

## Vessel Attachment Decision

The attachment store will support exactly one owner: a declaration or a
vessel. Vessel files use the same extension, 12 MB, magic-byte validation,
quarantine storage, scanner boundary, checksum, and tenant isolation as
declaration files.

The vessel editor will show existing files and allow authorized port/admin
users to add files after the vessel record has been saved. Attachment failures
must not silently report the entire vessel save as successful.

## Verification

1. Migration upgrades and downgrades the attachment ownership constraint.
2. API tests prove tenant isolation, validation, upload, listing, and deletion.
3. Historical tests prove cumulative imports keep confirmed duplicates,
   preserve reviewed vessel links, stage only additions, and retain the
   explicit correction path.
4. Frontend tests prove the vessel editor exposes existing/new attachments and
   the historical UI names the incremental merge behavior.
5. Targeted and full suites run against PostgreSQL.

## Claim Boundary

This design governs application data behavior only. It does not claim that CVF
controls an AI provider and therefore does not use mock output as governance
evidence.
