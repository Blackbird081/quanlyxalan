# Report Source UI/UX & PostgreSQL Local Verification Report

Date: 2026-08-03

Environment: Local Application (`http://127.0.0.1:8080`)

Database Engine: PostgreSQL 16.11 local executable evidence (`cangvu_ui_test` on `127.0.0.1:5432`); PostgreSQL 17 coverage remains in the regression suite

Latest Execution Timestamp: 2026-08-03T09:07:57+07:00

Role / User: Platform Admin (`admin`)
Evidence Directory: [docs/reviews/evidence/REPORT_SOURCE_UI_UX_20260803](evidence/REPORT_SOURCE_UI_UX_20260803/)

---

## 1. Executive Summary

This report documents the local end-to-end UI/UX and database export verification for the PL.02/PL.03 report source integration changes in `quanlyxalan`.

Verification was conducted against a dedicated local PostgreSQL 16.11 test database (`cangvu_ui_test`) pre-seeded with 4 distinct business test states (`LIVE_ONLY`, `HISTORICAL_ONLY`, `COMBINED_NON_OVERLAP`, and `COMBINED_OVERLAP`). The broader regression suite separately covers PostgreSQL 17. No mock JSON API responses were used for backend logic verification. Visual layout, navigation, source selector state, and responsive behavior were captured using a live Chromium browser instance.

---

## 2. Test Environment Setup & Seed Data

- Database Provisioning & Seed Script: [setup_ui_test_env.py](evidence/REPORT_SOURCE_UI_UX_20260803/setup_ui_test_env.py)
- Engine Verification Script: [verify_reports_engine.py](evidence/REPORT_SOURCE_UI_UX_20260803/verify_reports_engine.py)
- Database Name: `cangvu_ui_test` (Host: `127.0.0.1:5432`)
- Seed Safety Controls:
  - Enforces `QLXL_ALLOW_RESET_TEST_DB=1` environment flag.
  - Strictly restricts host target to local `127.0.0.1`/`localhost`/`::1`.
  - Strictly restricts target database name to `cangvu_ui_test`.
  - Sanitizes log output to prevent credential leaking.
- Test Scenarios Seeded:
  1. **LIVE_ONLY (2026-05):** Approved LIVE declaration (`DECL-202605-001`), no TOS import.
  2. **HISTORICAL_ONLY (2026-04):** Committed TOS Berth (`voyage 0004`) and matched Cargo detail (25 tonnes, 2 TEU), no LIVE declaration.
  3. **COMBINED_NON_OVERLAP (2026-07 TOS & 2026-08 LIVE):** TOS Berth/Detail in July 2026, Approved LIVE declaration in August 2026.
  4. **COMBINED_OVERLAP (2026-07):** Both TOS Berth/Detail and Approved LIVE declaration (`DECL-202607-001`) in July 2026.

---

## 3. Detailed Results Matrix

### A. Desktop Viewport (Configured: 1440 × 900 px | Actual Screenshot: 1784 × 1009 px) - `#reports`

| Criteria | Result | Observations & Screenshot Evidence |
| :--- | :---: | :--- |
| Single Selector "Nguồn PL.02 / PL.03" | PASS | Single segmented control under "NGUỒN XUẤT PHỤ LỤC". |
| Options LIVE, LỊCH SỬ / TOS, KẾT HỢP | PASS | Rendered cleanly with distinct active state styling. |
| PL.01 fixed badge | PASS | PL.01 card displays fixed badge "Nguồn: LIVE cố định". |
| PL.02 & PL.03 source labels update | PASS | Labels update dynamically: `LIVE`, `LỊCH SỬ / TOS`, `KẾT HỢP`. |
| Explanatory subtitle text | PASS | Concise text accurately reflects active source mode. |
| PL.02 adjustment section visibility | PASS | Section visible ONLY when `LIVE` is selected; hidden under `LỊCH SỬ / TOS` and `KẾT HỢP`. |

**Screenshots:**
- LIVE Mode: [desktop_reports_live_1785720429122.png](evidence/REPORT_SOURCE_UI_UX_20260803/desktop_reports_live_1785720429122.png) (1784 × 1009 px)
- LỊCH SỬ / TOS Mode: [desktop_reports_historical_1785720435918.png](evidence/REPORT_SOURCE_UI_UX_20260803/desktop_reports_historical_1785720435918.png) (1784 × 1009 px)
- KẾT HỢP Mode: [desktop_reports_combined_1785720442444.png](evidence/REPORT_SOURCE_UI_UX_20260803/desktop_reports_combined_1785720442444.png) (1784 × 1009 px)

---

### B. Mobile Viewport (Configured: 390 × 844 px | Actual Screenshot: 628 × 939 px) - `#reports`

| Criteria | Result | Observations & Screenshot Evidence |
| :--- | :---: | :--- |
| Analytics source buttons fit without overflow | PASS | The dashboard analytics source control is visible without horizontal overflow. |
| Cards and labels legible | PASS | Column layout with clear typography and touch-friendly targets. |
| Excel Export buttons | PASS_WITH_LIMITATION | PL.01 and PL.02 are fully visible; the PL.03 button is partially outside the captured viewport and remains reachable by scrolling. |
| No horizontal scrollbar | PASS | Layout fits viewport cleanly. |
| PL.02/PL.03 source selector | NOT_DIRECTLY_CAPTURED | Card badges prove the selected `KẾT HỢP` state, while the dedicated annex selector itself is outside the two saved mobile frames. Static responsive coverage verifies its three-column mobile layout. |

**Screenshots:**
- Mobile Reports Top View: [mobile_reports_top_1785720454043.png](evidence/REPORT_SOURCE_UI_UX_20260803/mobile_reports_top_1785720454043.png) (628 × 939 px)
- Mobile Reports Annexes View: [mobile_reports_annexes_1785720465695.png](evidence/REPORT_SOURCE_UI_UX_20260803/mobile_reports_annexes_1785720465695.png) (628 × 939 px)

---

### C. PostgreSQL Export Engine & Workbook Verification

| Criteria | Result | Verification Log / Artifact Evidence |
| :--- | :---: | :--- |
| PL.01 sends `source=live` | PASS | API contract enforced. Export succeeds with 200 OK. Non-LIVE returns status 422 refusal. Sample: [PL01_LIVE_sample.xlsx](evidence/REPORT_SOURCE_UI_UX_20260803/PL01_LIVE_sample.xlsx). Log: [422_pl01_invalid_source.log](evidence/REPORT_SOURCE_UI_UX_20260803/422_pl01_invalid_source.log). |
| PL.02 historical derives from TOS facts | PASS | Aggregates trips, tonnes (25), and TEUs (2) for April 2026. Sample: [PL02_TOS_sample.xlsx](evidence/REPORT_SOURCE_UI_UX_20260803/PL02_TOS_sample.xlsx). |
| Unsupported historical metrics remain blank | PASS | Missing dry/liquid metrics rendered as `None`/blank cells, not zero. Verified in [workbook_verification_receipt.json](evidence/REPORT_SOURCE_UI_UX_20260803/workbook_verification_receipt.json). |
| PL.03 historical has 1 row per Berth call | PASS | Per-call voyage/timeline grouping verified (2 distinct rows for barge `SG-9999` in July 2026 with ATB `10/07/2026 08:00:00` and `22/07/2026 09:00:00`). Sample: [PL03_TOS_sample.xlsx](evidence/REPORT_SOURCE_UI_UX_20260803/PL03_TOS_sample.xlsx). |
| PL.02 combined non-overlapping export | PASS | April 2026 TOS plus May 2026 LIVE exported successfully. Sample: [PL02_COMBINED_sample.xlsx](evidence/REPORT_SOURCE_UI_UX_20260803/PL02_COMBINED_sample.xlsx). |
| PL.03 combined non-overlapping export | PASS | April 2026 TOS plus May 2026 LIVE exported successfully. Sample: [PL03_COMBINED_sample.xlsx](evidence/REPORT_SOURCE_UI_UX_20260803/PL03_COMBINED_sample.xlsx). |
| PL.02/PL.03 overlapping exports blocked | PASS | Both appendices return HTTP 409 for July 2026. Logs: [PL.02 409](evidence/REPORT_SOURCE_UI_UX_20260803/409_appendix2_overlap_block.log) and [PL.03 409](evidence/REPORT_SOURCE_UI_UX_20260803/409_appendix3_overlap_block.log). |

**Execution Log & Receipt:**
- Engine Execution Log: [test_execution_log.txt](evidence/REPORT_SOURCE_UI_UX_20260803/test_execution_log.txt)
- Workbook Verification Receipt: [workbook_verification_receipt.json](evidence/REPORT_SOURCE_UI_UX_20260803/workbook_verification_receipt.json)

---

### D. Import Page - `#import` (Tab `Lịch sử / TOS`)

| Criteria | Result | Observations & Screenshot Evidence |
| :--- | :---: | :--- |
| Tab `Lịch sử / TOS` active | PASS | Tab header `Lịch sử / TOS` is visibly selected and active. |
| PL.03 shortcut section visible | PASS | Dedicated card for PL.03 export shortcut rendered clearly. |
| TOS source explanation text | PASS | Text explicitly explains PL.03 uses the same TOS source as Activity Report. |
| Export PL.03 button visible | PASS | "Xuất PL.03" button active and clickable. |
| Layout distinction | PASS | Clearly separated from "Dữ liệu vận hành" import tab to prevent user confusion. |

**Screenshots:**
- Desktop Import TOS Tab View: [desktop_import_tos_1785720413049.png](evidence/REPORT_SOURCE_UI_UX_20260803/desktop_import_tos_1785720413049.png) (Configured: 1440 × 900 px | Actual: 1784 × 1009 px)
- Mobile Import Tab View: [mobile_import_tabs_1785720482595.png](evidence/REPORT_SOURCE_UI_UX_20260803/mobile_import_tabs_1785720482595.png) (Configured: 390 × 844 px | Actual: 628 × 939 px)
- Mobile Import Shortcut View: [mobile_import_shortcut_1785720487651.png](evidence/REPORT_SOURCE_UI_UX_20260803/mobile_import_shortcut_1785720487651.png) (Configured: 390 × 844 px | Actual: 628 × 939 px)

---

## 4. Evidence Artifacts Index

All evidence files are stored relative to this report in [docs/reviews/evidence/REPORT_SOURCE_UI_UX_20260803/](evidence/REPORT_SOURCE_UI_UX_20260803/):

### Scripts & Utilities
- Seed & Provisioning Script: [setup_ui_test_env.py](evidence/REPORT_SOURCE_UI_UX_20260803/setup_ui_test_env.py)
- Engine Verification Script: [verify_reports_engine.py](evidence/REPORT_SOURCE_UI_UX_20260803/verify_reports_engine.py)

### Execution Logs & Receipts
- Comprehensive Test Log: [test_execution_log.txt](evidence/REPORT_SOURCE_UI_UX_20260803/test_execution_log.txt)
- Contract Refusal Log (PL.01): [422_pl01_invalid_source.log](evidence/REPORT_SOURCE_UI_UX_20260803/422_pl01_invalid_source.log)
- PL.02 Overlap Conflict Log (409): [409_appendix2_overlap_block.log](evidence/REPORT_SOURCE_UI_UX_20260803/409_appendix2_overlap_block.log)
- PL.03 Overlap Conflict Log (409): [409_appendix3_overlap_block.log](evidence/REPORT_SOURCE_UI_UX_20260803/409_appendix3_overlap_block.log)
- JSON Verification Receipt: [workbook_verification_receipt.json](evidence/REPORT_SOURCE_UI_UX_20260803/workbook_verification_receipt.json)

### Representative Sample Workbook Output (No Prod Data)
- PL.01 LIVE Sample: [PL01_LIVE_sample.xlsx](evidence/REPORT_SOURCE_UI_UX_20260803/PL01_LIVE_sample.xlsx)
- PL.02 TOS Sample: [PL02_TOS_sample.xlsx](evidence/REPORT_SOURCE_UI_UX_20260803/PL02_TOS_sample.xlsx)
- PL.03 TOS Sample: [PL03_TOS_sample.xlsx](evidence/REPORT_SOURCE_UI_UX_20260803/PL03_TOS_sample.xlsx)
- PL.02 COMBINED Sample: [PL02_COMBINED_sample.xlsx](evidence/REPORT_SOURCE_UI_UX_20260803/PL02_COMBINED_sample.xlsx)
- PL.03 COMBINED Sample: [PL03_COMBINED_sample.xlsx](evidence/REPORT_SOURCE_UI_UX_20260803/PL03_COMBINED_sample.xlsx)

### Screenshots
- Desktop Import TOS: [desktop_import_tos_1785720413049.png](evidence/REPORT_SOURCE_UI_UX_20260803/desktop_import_tos_1785720413049.png)
- Desktop Reports LIVE: [desktop_reports_live_1785720429122.png](evidence/REPORT_SOURCE_UI_UX_20260803/desktop_reports_live_1785720429122.png)
- Desktop Reports LỊCH SỬ / TOS: [desktop_reports_historical_1785720435918.png](evidence/REPORT_SOURCE_UI_UX_20260803/desktop_reports_historical_1785720435918.png)
- Desktop Reports KẾT HỢP: [desktop_reports_combined_1785720442444.png](evidence/REPORT_SOURCE_UI_UX_20260803/desktop_reports_combined_1785720442444.png)
- Mobile Reports Top: [mobile_reports_top_1785720454043.png](evidence/REPORT_SOURCE_UI_UX_20260803/mobile_reports_top_1785720454043.png)
- Mobile Reports Annexes: [mobile_reports_annexes_1785720465695.png](evidence/REPORT_SOURCE_UI_UX_20260803/mobile_reports_annexes_1785720465695.png)
- Mobile Import Tabs: [mobile_import_tabs_1785720482595.png](evidence/REPORT_SOURCE_UI_UX_20260803/mobile_import_tabs_1785720482595.png)
- Mobile Import Shortcut: [mobile_import_shortcut_1785720487651.png](evidence/REPORT_SOURCE_UI_UX_20260803/mobile_import_shortcut_1785720487651.png)

### Evidence limitations

- The saved mobile report frames do not directly include the dedicated
  `NGUỒN XUẤT PHỤ LỤC` selector; they show the analytics selector and the
  selected source badges on PL.02/PL.03. The responsive selector contract is
  covered by `tests/test_frontend_ux.py`.
- A new browser session was unavailable during independent publication review,
  so no substitute or mock screenshot was added.
- Local executable receipts use PostgreSQL 16.11. PostgreSQL 17 compatibility
  is supported by the separate regression-suite evidence cited in the
  integration review.
