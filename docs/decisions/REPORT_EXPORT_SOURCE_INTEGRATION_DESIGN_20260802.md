# Report Export Source Integration Design

Decision ID: DESIGN-QLXL-REPORT-EXPORT-SOURCE-20260802

Status: APPROVED_BY_OPERATOR

Phase: DESIGN

Risk: R2

## Context

The three report cards currently call the LIVE declaration export route. TOS
Berth, TOS cargo detail and previously reported PL.03 are already retained and
used by analytics plus a separate PL.03 shortcut, but they are not presented as
an export source in Activity Reports.

## Decisions

1. Add one compact source selector labelled `Nguồn PL.02 / PL.03` above the
   report filters. Do not repeat a selector inside every report card.
2. PL.01 remains explicitly `LIVE cố định`; the selector never changes it.
3. PL.02 supports:
   - LIVE: existing approved declarations and existing adjustments;
   - LỊCH SỬ / TOS: calls from active validated Berth facts and container
     tonnes/TEU from matched valid cargo facts;
   - KẾT HỢP: LIVE plus historical only when their coverage months do not
     overlap.
4. Historical PL.02 leaves unsupported dry/liquid/foreign/passenger metrics
   blank. Missing facts must never be converted to zero.
5. PL.03 supports:
   - LIVE: existing approved declarations;
   - LỊCH SỬ / TOS: one row per Berth call, cargo/time from TOS and legacy
     PL.03/current register dimensions;
   - KẾT HỢP: concatenate non-overlapping LIVE and historical timelines.
6. Combined export returns a clear conflict when any month in the requested
   range has both LIVE and historical coverage.
7. The existing Import-page PL.03 action remains as a labelled quick shortcut
   using the same TOS source, avoiding removal of an established workflow.
8. Source badges and a short contextual explanation update immediately. The
   PL.02 adjustment editor is shown only for LIVE to avoid applying an
   unlabelled manual adjustment to historical facts.

## Rejected Alternatives

- One selector per card: rejected because it repeats controls and increases
  visual noise.
- A selector labelled as applying to all PL reports: rejected because the
  available three imports cannot reconstruct a trustworthy PL.01.
- Silent combination of overlapping months: rejected because it can double
  count voyages, tonnes and TEU.

## Claim Boundary

This is application reporting behavior, not AI-governance behavior. No live
provider claim is made.
