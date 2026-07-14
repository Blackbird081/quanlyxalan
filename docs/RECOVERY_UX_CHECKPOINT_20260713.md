# Recovery UX Checkpoint — 2026-07-13

## Tranche

- ID: RECOVERY-UX-T1
- Status: CLOSED — visual and behavioral regression tests passed, branch is ready for Gate 5 closure
- Branch: `recovery/frontend-baseline-20260712`
- Baseline: `929a8c487c572b7bcad859e237b17da1d494a1db`
- Worktree: `Khai-bao-Cang-vu-recovery-ux`

## Controlled scope

This branch is isolated from both the active `main` worktree and the pristine
restore copy. Neither comparison source was edited.

Implemented in this checkpoint:

1. Restored a styled "Báo cáo hoạt động Cảng" block with tabs PL.01-PL.03.
2. Disabled analytics filters and download buttons with warning text: "Thống kê sản lượng chưa khả dụng".
3. Hid the external integration sync panel from Customer and Port Staff pages in app.js using style.display logic.
4. Converted the select multiple input in wizard step 4 to a friendly checkbox list.
5. Sized sidebar menu SVG icons to 16px to prevent layout breakage on mobile.

## Evidence

- CVF workspace enforcement doctor: PASS 17/17.
- `python -m pytest -q`: PASS 67/67.
- Migration `g06f0f000006` reached head on the isolated demo database; roles are
  `ADMIN`, `CUSTOMER`, `PORT_STAFF`, statuses are canonical, and no legacy
  declaration columns remain.
- Live API check: retired `QLC_APPROVE` returned HTTP 410; `PORT_APPROVE`
  released the previously stuck demo declaration id 8 to `APPROVED`.
- Backend contract test proves that the port employee can either approve the
  submitted declaration directly or request changes.
- Static checks contain no visible `Chờ CV`, `Chờ QLC`, `Chờ BP`, or
  `CV → QLC → BP` strings in `frontend/`.
- Live API reproduction before commit `5e74643`: Analytics returned 404 and
  customer access to integration returned 403. The frontend now avoids both
  invalid calls and regression remains PASS 67/67.
- **Browser/UAT evidence (2026-07-14):** ALL PASSED. All critical issues (wizard crash, integration panel CSS leak, mobile sidebar layout) have been fixed and visually verified on the real browser. Detailed evidence recorded in [BROWSER_EVIDENCE_RECOVERY_UX_20260714.md](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/BROWSER_EVIDENCE_RECOVERY_UX_20260714.md).

## Not completed in this checkpoint

- Analytics restoration or implementation. The baseline frontend calls an
  analytics endpoint that is not present in the historical backend.
- **RESOLVED (2026-07-14):** Live browser screenshot evidence. Multi-role multi-viewport visual testing has been completed. Gate 5 is READY (PASS).

## Active risk

No active risks. All visual regressions are resolved.
