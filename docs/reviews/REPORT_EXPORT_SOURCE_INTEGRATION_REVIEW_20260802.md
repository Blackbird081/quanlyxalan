# Report Export Source Integration Review

Review ID: REVIEW-QLXL-REPORT-EXPORT-SOURCE-20260802

Work order: [WO_QLXL_REPORT_EXPORT_SOURCE_INTEGRATION_20260802.md](../work_orders/WO_QLXL_REPORT_EXPORT_SOURCE_INTEGRATION_20260802.md)

Disposition: PASS_WITH_LIMITATIONS

Risk: R2

## Scope Review

- Existing PL.01/PL.02/PL.03 API calls remain LIVE by default.
- PL.01 rejects non-LIVE requests and the UI labels it `LIVE cố định`.
- Historical PL.02 derives calls from valid Berth facts and container tonnes/TEU from valid matched cargo facts for current month and year-to-date.
- Historical PL.02 leaves unsupported dry/liquid/foreign/passenger fields blank; incomplete TOS coverage is not converted into zero.
- Historical PL.03 reuses the per-call TOS assembler and applies the requested date boundary. Each Berth call retains its own cargo totals and ATB/ATD.
- Combined PL.02/PL.03 rejects any requested month containing both approved LIVE and historical/TOS coverage.
- Combined non-overlapping PL.02 sums only supported facts. Combined PL.03 excludes blank register-only rows, sorts rows by operating time and renumbers them.
- Historical and combined sources remain restricted to reporting-unit-scoped Port users. Customer access receives 403.
- One compact selector controls PL.02 and PL.03. PL.01 is visually fixed to LIVE, each affected card repeats the selected source, explanatory copy is short and contextual, and the PL.02 adjustment editor is hidden outside LIVE.
- The Import-page PL.03 action is retained and clearly labelled as a shortcut using the same historical/TOS source under the `Lịch sử / TOS` tab.

## Review Findings And Repairs

- MEDIUM: combined PL.03 initially required historical coverage and therefore failed when the selected range contained only LIVE data. The historical collector now supports an optional empty result for combined mode while historical-only mode still returns a clear 409.
- LOW: combined PL.03 initially concatenated historical rows before LIVE rows, which could display a non-chronological timeline. The final output now sorts both sources by operating time and renumbers rows.
- LOW: the fixed-source badge referenced an undefined theme token. It now uses an existing elevated-surface token.
- Re-review result: all findings are resolved. No open HIGH, MEDIUM or LOW finding remains.

## Executable Evidence

- Rendered UI browser evidence (Desktop 1440 × 900 px & Mobile 390 × 844 px) captured and verified in [REPORT_SOURCE_UI_UX_TEST_REPORT_20260803.md](REPORT_SOURCE_UI_UX_TEST_REPORT_20260803.md).
- Local PostgreSQL 16.11 test DB (`cangvu_ui_test`) executable verification passed all four business scenarios (`LIVE_ONLY`, `HISTORICAL_ONLY`, `COMBINED_NON_OVERLAP`, `COMBINED_OVERLAP`) via [verify_reports_engine.py](evidence/REPORT_SOURCE_UI_UX_20260803/verify_reports_engine.py); separate regression evidence covers PostgreSQL 17.
- Safety-guarded DB seed script [setup_ui_test_env.py](evidence/REPORT_SOURCE_UI_UX_20260803/setup_ui_test_env.py) verifies the explicit reset flag, target host/database and the local admin host/database that executes the reset.
- Workbook verification receipt saved to [workbook_verification_receipt.json](evidence/REPORT_SOURCE_UI_UX_20260803/workbook_verification_receipt.json) and execution log saved to [test_execution_log.txt](evidence/REPORT_SOURCE_UI_UX_20260803/test_execution_log.txt).
- Relative repository links established across all evidence artifacts in [docs/reviews/evidence/REPORT_SOURCE_UI_UX_20260803/](evidence/REPORT_SOURCE_UI_UX_20260803/).
- Publication rerun on the local host: 281 passed and 2 backup-only tests failed because `pg_dump` is absent from `PATH`; the two existing openpyxl warnings remain. Earlier PostgreSQL 17 regression evidence covered the report-source scenarios, and the PR quality gate is expected to supply the matching PostgreSQL 17 client for the backup tests.

## Limitations

- Two backup-only tests fail on this host because the required `pg_dump` executable is absent; they are unrelated to report source integration and remain a publication limitation until the GitHub quality gate runs with its PostgreSQL 17 client.
- Rendered UI/UX browser evidence (Desktop 1440 × 900 & Mobile 390 × 844) and local PostgreSQL 16.11 executable results have been captured and saved to [docs/reviews/evidence/REPORT_SOURCE_UI_UX_20260803/](evidence/REPORT_SOURCE_UI_UX_20260803/) and detailed in [REPORT_SOURCE_UI_UX_TEST_REPORT_20260803.md](REPORT_SOURCE_UI_UX_TEST_REPORT_20260803.md).
- The saved mobile report frames show responsive analytics controls and PL.02/PL.03 source badges, but do not directly include the dedicated annex-source selector. Its three-column mobile layout remains covered by the frontend static suite; no browser session was available to add another independent frame.
- No production data was read, altered or migrated.
- Commit, push, merge, deployment and FREEZE remain unauthorized.

## Claim Boundary

This review covers application reporting, XLSX generation, RBAC and UI source clarity. It makes no AI-governance claim and requires no live provider proof.
