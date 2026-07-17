# Appendix Business Decision Register — 2026-07-17

Status: BUSINESS DECISIONS APPROVED — READY FOR DESIGN; CODE NOT AUTHORIZED
Project phase: DESIGN
Risk level: R2
Source owner: Project owner / port-domain user

## 1. Source and review method

Source file: local owner-response document `AI.docx` (not published)
SHA-256: `D8B17B7313FF873BB1652538888D95AFED48D4B667825CFC4C32C92C31F80CE1`

The file was reviewed read-only with the Documents skill and its bundled
Python runtime. All 55 paragraphs were extracted and the DOCX package was
checked structurally. The document contains no tables, comments, comment
anchors, tracked insertions or tracked deletions.

The project owner then answered all seven remaining confirmations directly on
2026-07-17 and supplied screenshots of the PL.02 monthly form and the PL.03
35-column form. Those direct confirmations supersede the earlier ambiguous
status where explicitly stated below.

The required `render_docx.py` run was attempted, but the runtime could not find
LibreOffice/`soffice` (`FileNotFoundError: [WinError 2]`). Therefore no page PNG
was produced and visual page-layout QA remains unverified. This does not block
the textual business-decision review, but no visual claim is made about the
source DOCX.

The answers were compared with:

- `docs/APPENDIX_EXPORT_VERIFICATION_20260716.md`;
- `docs/APPENDIX_TEMPLATE_AUDIT_20260716.md`;
- `docs/REPORT_MAPPING_SPEC.md` (`KBCV-REPORT-MAP-1.0`);
- `docs/CANONICAL_DATA_AND_APPENDIX_ASSURANCE_ROADMAP_20260716.md`;
- `docs/AGENT_HANDOFF.md`.

## 2. Faithful summary of the owner's answers

- PL.01 is a daily report from approved declarations. The full Salan register
  is a separate internal dashboard/register product for Port staff and Port
  leadership; it is not the PL.01 row population.
- PL.02 is one official form per calendar month. It contains the selected
  month's values and cumulative values from January through that month. The web
  application also needs a separate analytical reporting dashboard.
- PL.03 has one row per Salan/vessel in the reporting output, aggregating the
  eligible customer declarations submitted to the Port for that vessel.
- Arrival uses ATA, falling back to ETA. Departure uses ATD, falling back to
  ETD. `declaration_date` is the form creation date, not the operating date.
- PL.02 vessel calls are counted by arrival. Port staff and ADMIN may make a
  controlled manual adjustment; the adjustment must be explicit and auditable.
- PL.01/H is design passenger capacity. PL.01/O is actual crew/passenger count.
- Arrival and departure positions are berth/port positions. Departure needs a
  dedicated value because a vessel can shift berth within the same port.
- PL.03/AE is `Cảng đến/Cảng làm hàng = working_port`; PL.03/AF is the next
  destination `destination_port`. Destination must not be used as PL.01/K.
- PL.03/AI retains the official label `Đại lý PTND` and reports the value
  declared by the customer for the approved call; it is not inferred later.
- No activity and activity with no cargo/passengers are both blank, optionally
  with light-gray fill. A passenger vessel that berths counts as a passenger
  call even when it carries zero passengers.
- PL.02 includes load and unload/export and import production across all
  vessels, grouped by cargo type. Cumulative values run from January 1 through
  the report date.
- Static report fields use the latest information currently supplied to the
  Port. The customer is responsible for notifying the Port of changes.
- The official workbook should follow the complete form. PL.02 must retain
  `tháng báo cáo`. PL.03 does not require the preparer/authority signature block.
- PL.03 labels are standardized to `TEUs`, `TEUs Rỗng` and `Quá cảnh` through
  an approved template/export revision.
- The regulation and forms are newly issued and may still be adjusted by the
  owner before the first reporting cycle.

## 3. Decision Register

| Decision ID | Appendix/column | Business question | Owner answer | Status | Canonical mapping impact | DB/schema impact | UI/workflow impact | Exporter impact | Required acceptance test |
|---|---|---|---|---|---|---|---|---|---|
| BD-01 | PL.01 scope | Approved daily calls or all Salan vessels? | PL.01 uses approved daily declarations; all Salan vessels belong to the separate internal register/dashboard | CONFIRMED | PL.01 remains activity-driven; register rows cannot fabricate calls | No new field | Keep external appendix reports separate from the internal Salan dashboard | Do not mix static register rows into PL.01 | Approved call appears in PL.01; static-only vessel appears only in the internal register/dashboard |
| BD-02 | PL.02 period | Monthly form or arbitrary range? | One month per official form; current-month columns plus cumulative January-through-selected-month columns; separate web dashboard required | CONFIRMED | Official PL.02 period is a calendar month; analytics are a separate projection | No new field necessarily | Month selector for official export; analytical dashboard may support week/month/year/range | Preserve `tháng báo cáo` and YTD columns | July export contains July values and January–July cumulative values |
| BD-03 | PL.03 row grain | One row per call/cargo item or per vessel? | One Salan/vessel per row, aggregating its eligible customer declarations | CONFIRMED | Replace cargo-row expansion with vessel-period aggregation | Keep cargo/call facts separately; aggregate by canonical vessel identity at report time | Drill-down must preserve contributing declarations | Emit one row per vessel and aggregate cargo category measures | Multiple declarations/cargo items for one vessel produce one row; drill-down totals reconcile |
| BD-04 | All appendices | Eligible workflow state | PL.01 explicitly approved-only; current approved spec already makes all reports approved-only and is not contradicted | CONFIRMED | Retain `APPROVED`, tenant-scoped eligibility | None | Status eligibility remains governed | Exclude draft/pending/revoked/cancelled | Same data in DRAFT is absent; after APPROVED it appears |
| BD-05 | PL.01/J, PL.03/AG | Arrival time precedence | ATA, otherwise ETA | CONFIRMED | Operating arrival time is `ATA ?? ETA` | ATA field already exists | Controlled ATA entry/confirmation needed | Do not use `declaration_date` | ATA overrides ETA; ETA is used only when ATA is blank |
| BD-06 | PL.01/L, PL.03/AH | Departure time precedence | ATD, otherwise ETD | CONFIRMED | Operating departure time is `ATD ?? ETD` | ATD field already exists | Controlled ATD entry/confirmation needed | Do not use `declaration_date` | ATD overrides ETD; ETD is used only when ATD is blank |
| BD-07 | PL.02 cross-month call | Call arrives and departs in different months | Count by arrival; Port staff/ADMIN may adjust manually | CONFIRMED | Default `Lượt tàu` membership uses operating arrival date | Adjustment record needs actor, reason, before/after and report month | Authorized adjustment workflow with visible warning and audit trail | Apply default arrival count plus approved adjustment only | Arrival in M/departure in M+1 counts in M by default; authorized adjustment is traceable |
| BD-08 | Report filter | Meaning of `declaration_date` | Form creation date | CONFIRMED | Must not be the operating-period filter | None | Display as creation metadata | Replace current report-period filter | Changing creation date does not move an operating event between report months |
| BD-09 | PL.01/H | Capacity or actual passengers? | Design passenger capacity | CONFIRMED | Static `passenger_capacity`; no fallback to `passenger_count` | Existing vessel field is sufficient | Validate capacity for passenger vessel | Remove activity fallback | Missing capacity stays blank even when actual passenger count is positive |
| BD-10 | PL.01/O | Actual crew/passenger count? | Yes | CONFIRMED | Activity `crew_count/passenger_count` | Existing fields sufficient | Retain event entry | Format actual values only | Design capacity never appears in PL.01/O |
| BD-11 | PL.01/I,K | Arrival/departure berth | Arrival/working position uses the call's working port/berth; departure needs a separate value because the vessel may shift berth | CONFIRMED | PL.01/I uses approved working/arrival position; PL.01/K uses departure berth | Add event snapshot `departure_berth`; retain clear working/arrival position | Berth entry and intra-port shift workflow needed | Never substitute destination port | Same-berth and shifted-berth cases export correctly |
| BD-12 | PL.03/AE,AF | Working port versus destination port | AE=working port/cargo-working port; AF=next destination port | CONFIRMED | Preserve AE=`working_port`, AF=`destination_port` | Existing concepts sufficient | Labels/source preview must remain distinct | Export each field to its confirmed column | Known call exports different working/destination ports into AE/AF |
| BD-13 | PL.03/AI | Meaning and source of `Đại lý PTND` | Report exactly what the customer declares in the Port form; keep the official column name | CONFIRMED | Use an approved declaration snapshot; do not infer from current company later | Add dedicated `agent_ptnd_name` snapshot or equivalent explicit field | Customer web/import form must capture it; correction uses governed workflow | Keep label `Đại lý PTND` and export snapshot | Owner-operated and hired-vessel declarations preserve their entered agent values |
| BD-14 | PL.02/C:P | No eligible activity | Blank; optional light-gray fill | CONFIRMED | Missing aggregate is blank, not numeric zero | None | Optional gray presentation | Stop initializing visible no-data cells to zero | Empty dataset produces blanks; no false production |
| BD-15 | PL.02/C:P | Call exists but no cargo/passengers | Blank; optional light-gray fill | CONFIRMED | Missing measure remains blank | Need nullable/absence semantics in aggregation | UI distinguishes missing from measured zero | Do not emit synthetic zero | Cargo-less/passenger-less call leaves relevant cells blank |
| BD-16 | PL.02/O | Passenger call with zero passengers | If a passenger vessel berths, it counts | CONFIRMED | Cannot use `passenger_count > 0`; use approved passenger-vessel/call classification | DESIGN chooses explicit `is_passenger_call` snapshot or a proven canonical classifier | Show/confirm passenger-call classification | Count the call even when passenger total is blank/zero | Passenger vessel with zero passengers increments passenger calls only |
| BD-17 | PL.02 cargo | Load and unload inclusion | Total includes import/export of all vessels, grouped by cargo type | CONFIRMED | Aggregate all eligible load/unload items once | Existing JSON is usable; normalized cargo model remains desirable | Review item classification | Avoid omission and double count | One call with load+unload contributes both exactly once |
| BD-18 | PL.02 cumulative | Cumulative start | January 1 through report date | CONFIRMED | Preserve YTD cumulative rule | None | Date control must show/report basis | Keep original monthly labels | January and later-month fixtures produce correct YTD totals |
| BD-19 | Static columns | Current master or approval snapshot? | Latest information currently provided to the Port | CONFIRMED for vessel/master facts | Current vessel/profile/contact wins where mapping identifies static data | Preserve provenance and update audit | Warn/record controlled master updates | Use current static values; retain activity snapshot facts | Master update changes static report cells but not historical cargo/passenger activity |
| BD-20 | PL.01/PL.02 form | Full form or table only? | Following the complete form is best | CONFIRMED | Supersedes current table-only scope for PL.01/PL.02 | None | Capture report header inputs/config | Add title/date/month/company/note blocks | Export visually contains all required form blocks |
| BD-21 | PL.02 wording | `tháng` or `kỳ`? | Must use `tháng báo cáo`; do not use `kỳ báo cáo` | CONFIRMED | Official monthly semantics are authoritative | None | UI may still offer analysis ranges, but official label is fixed | Restore original wording | Header matches the source form exactly |
| BD-22 | PL.03 signature | Signature block required? | No | CONFIRMED exception | Missing signature is approved for PL.03 export | None | None | Do not add signature block | Export ends after data without signature and matches approved exception |
| BD-23 | PL.03 labels | Correct `Tues`/`Quá cảng` or preserve template? | Correct to `TEUs`, `TEUs Rỗng`, `Quá cảnh` | CONFIRMED | Canonical labels are standardized | None | Use the corrected labels consistently | Update approved template/export labels | All headers use the approved spellings exactly |

## 4. APPX and MAP disposition

These statuses close or retain the **business decision**, not the code defect.
No implementation was changed in this review.

| ID | Decision status | Basis | Implementation status |
|---|---|---|---|
| APPX-01 | CLOSED | PL.01 should follow the complete form | OPEN — title/date/company/note must be implemented and verified |
| APPX-02 | CLOSED | PL.02 should follow the complete form | OPEN — title/month block must be implemented and verified |
| APPX-03 | CLOSED | Must use `tháng báo cáo`, not `kỳ báo cáo` | OPEN — exporter wording must be corrected |
| APPX-04 | CLOSED BY EXCEPTION | Owner explicitly says PL.03 signature block is not required | No signature implementation required; exception must enter the approved spec |
| MAP-01 | CLOSED | PL.01/H is static design capacity; PL.01/O is actual count | OPEN — remove cross-class fallback and add tests |
| MAP-02 | CLOSED | Departure berth is distinct; AE=working port and AF=destination port | OPEN IMPLEMENTATION — schema/UI/export design pending |
| MAP-03 | CLOSED | Official PL.02 is monthly; YTD is January-through-month; operating arrival controls call count; blank rules are approved | OPEN IMPLEMENTATION — query/aggregation/override workflow pending |
| MAP-04 | CLOSED | PL.03/AI keeps `Đại lý PTND` and uses the customer-declared approved snapshot | OPEN IMPLEMENTATION — dedicated field/import/UI pending |
| MAP-05 | CLOSED | PL.03 grain is one canonical vessel per reporting output, aggregating eligible declarations | OPEN DESIGN/IMPLEMENTATION — non-additive field aggregation and drill-down contract pending |

## 5. Field and UI implications

### ATA/ATD

- Database fields already exist: `actual_arrival_at` and
  `actual_departure_at`.
- Add controlled UI/workflow entry or confirmation and preserve ETA/ETD as
  separate estimates.
- No new DB field is required unless approval provenance cannot be represented
  by the existing declaration/event audit model.

### Arrival/departure berth

- `departure_berth` is required by the confirmed intra-port berth-shift case.
- PL.01/I uses the approved working/arrival position; DESIGN must give this
  value a precise field name and validation rule.
- Departure berth must be an event snapshot; it must not use
  `destination_port`.

### Agent/operator

- PL.03/AI needs a dedicated event-level `Đại lý PTND` snapshot populated from
  the customer's declaration/import.
- Do not infer or refresh this field from current company data after approval.

### Passenger-call classification

- `passenger_count > 0` is not a valid classifier.
- A passenger vessel that berths counts even with zero passengers.
- DESIGN must decide whether this is reliably derived from canonical vessel
  type/purpose or stored as an explicit `is_passenger_call` snapshot.

## 6. Owner confirmations received on 2026-07-17

1. PL.01 uses approved daily declarations; the Salan register/dashboard is a
   separate internal Port-management product.
2. PL.02 produces one official form per month with current-month and
   January-through-month cumulative columns; the web also needs an analytical
   dashboard.
3. PL.03 produces one row per Salan/vessel and aggregates the eligible customer
   declarations contributing to that vessel.
4. PL.02 counts calls by arrival; Port staff and ADMIN may make an explicit,
   audited manual adjustment.
5. PL.03 AE is working/cargo-working port; AF is the next destination port.
6. PL.03/AI keeps the official label `Đại lý PTND` and uses the value declared
   by the customer for the approved call.
7. Correct the labels to `TEUs`, `TEUs Rỗng` and `Quá cảnh`.

## 7. Phase conclusion

All APPX-01 through APPX-04 and MAP-01 through MAP-05 business decisions are
now closed. T0 is complete and the project may transition from REVIEW to
DESIGN.

This approval authorizes T1 data-contract and dashboard/report design only. It
does **not** authorize code, schema, UI, template or workbook implementation.
Before BUILD, DESIGN must define PL.03 aggregation for non-additive fields,
the audited PL.02 manual-adjustment model, exact new field names and acceptance
tests, then receive human review.
