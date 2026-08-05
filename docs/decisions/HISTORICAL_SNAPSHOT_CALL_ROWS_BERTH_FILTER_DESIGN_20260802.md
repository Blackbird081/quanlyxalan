# Historical Snapshot, Per-Call PL.03 And Berth Filter Design

Decision ID: ADR-QLXL-HISTORICAL-SNAPSHOT-CALL-BERTH-20260802

Status: APPROVED_BY_OPERATOR_SCOPE

Phase: DESIGN

Risk: R2

## Intent

Treat later cumulative TOS workbooks as replacement snapshots when they cover
the existing business identities, let Platform Admin remove obsolete history
receipts safely, export one PL.03 row per Salan call, and filter activity
analytics by the Berth column-H code.

## Snapshot Decision

For the same reporting unit, source kind and reporting scope, preview compares
stable business identities before staging:

- Berth: normalized vessel + year + voyage call key.
- Cargo detail: call key plus container size, full/empty, trade scope,
  movement method and direction, preserving multiplicity.
- Historical PL.03 scaffold: normalized registration, falling back to vessel
  name, within the selected reporting period.

If every active identity is represented in the new workbook, the workbook is
a cumulative snapshot. The preview stages the complete new workbook so later
ATB/ATD, berth and cargo-value updates survive. Confirmation activates that
snapshot and supersedes the older active receipts.

If any active identity is absent, the workbook is partial. Only genuinely new
facts are staged and explicit incremental confirmation keeps prior active
receipts. Missing facts are never interpreted as deletions.

This decision supersedes the earlier default that existing database values
always win over values repeated in a later cumulative workbook.

## Admin History Deletion

Platform Admin may permanently delete only `PREVIEWED`, `REJECTED` or
`SUPERSEDED` receipts in the active reporting unit. `COMMITTED` and `REVIEW`
receipts remain protected because reports depend on them. Cross-import cargo
dependencies block deletion rather than cascading silently. The database
receipt and owned staged rows are removed; the checksum-addressed source
archive is retained for operational recovery and is not exposed in the UI.

## PL.03 Row Grain

Historical PL.03 export uses each validated Berth call as the row grain. The
same Salan therefore appears on multiple rows when it has multiple voyages.
Each row receives only cargo linked to that call and that call's ATB/ATD.
Legacy PL.03 and the vessel register remain dimension sources. Berth code is
not added to the PL.03 template.

## Activity Berth Filter

Activity analytics accepts an optional berth code. Historical/TOS metrics
filter on the normalized Berth column-H value. LIVE metrics use the operating
berth/working-port value when the same filter is selected. The response
returns available berth values for the selected period/source, and Excel
analytics export applies the same filter.

## Claim Boundary

This decision changes application data and reporting behavior only. It does
not claim live AI-governance behavior.
