# Maritime Report Mapping Specification

- Spec id: `KBCV-REPORT-MAP-1.0`
- Status: APPROVED BY PROJECT OWNER
- Approval date: 2026-07-11
- Reporting unit: **Cảng Tân Thuận**
- Port label: **Cảng Sài Gòn-Cảng Tân Thuận**
- Source templates: `templates/Phụ lục 1.docx`, `templates/Phụ lục 2.docx`,
  `templates/Phụ lục 3.xlsx`

## Reporting period

- Users may choose an arbitrary `from` and `to` date using calendar controls.
- Default cumulative period is January 1 of the report year through the report
  end date.
- When dates are omitted, the application uses January 1 of the current year
  through today.

## Eligible declarations

- Include only declarations in `APPROVED` workflow state.
- Exclude `DRAFT`, pending review states, `CHANGES_REQUESTED`, cancelled and
  `REVOKED` declarations.
- Report queries remain tenant-scoped for CUSTOMER users.

## Arrival and departure times

- Arrival uses `actual_arrival_at` (ATA) when present; otherwise uses `eta`.
- Departure uses `actual_departure_at` (ATD) when present; otherwise uses `etd`.
- ETA, ETD, ATA and ATD remain distinct source fields for traceability.

## Template table structures

- Appendix 1 exports the 16-column `PHƯƠNG TIỆN` / `HOẠT ĐỘNG` table from
  `templates/Phụ lục 1.docx`.
- Appendix 2 exports the 16-column current-period and cumulative table from
  `templates/Phụ lục 2.docx`.
- Appendix 3 preserves the 35-column table, merged headers and cell formatting
  from `templates/Phụ lục 3.xlsx`.
- Only the table is reproduced; document titles and other cover information are
  outside the current scope.

## Vessel register inheritance

- A report row remains driven by an approved declaration/trip.
- When its registration number matches a vessel in Hồ sơ phương tiện / Sổ theo
  dõi Salan, current vessel name, type, class, dimensions, capacities,
  certificate expiry and tracked master contact take priority over the older
  declaration snapshot.
- Multiple operating-area profiles remain separate source records. Exported
  cells retain all corresponding deadweight and cargo-capacity values in their
  stored order instead of selecting or averaging one profile.
- Static register records alone do not fabricate a vessel call, cargo movement
  or passenger movement in an activity report.

## Cargo expansion and totals

- Emit one detail row for each non-empty cargo movement/type.
- Unload and load movements are distinct rows when both exist.
- Each detail row records cargo name, movement, tons, TEU and empty TEU.
- Appendix 2 provides period totals and year-to-report-date cumulative totals.
- Container conversion remains 20 feet = 1 TEU and 40 feet = 2 TEU.

## Import policy

- Imports use partial acceptance.
- Every rejected row returns its source row number and a safe validation error.
- Accepted rows commit independently through savepoints.
- Template/mapping version and source checksum must be recorded; repeat imports
  must be idempotent.

## Administrative editing

- ADMIN may edit data across organizations.
- Server-side validation, optimistic version checks and audit logging remain
  mandatory.
- Submitted/approved declaration changes must use the governed correction flow;
  ADMIN authority does not silently bypass snapshot or workflow rules.

## Approval boundary

This approval covers field mapping and selection rules. It does not approve
external transmission, legal acceptance by the Maritime Authority or production
deployment.
