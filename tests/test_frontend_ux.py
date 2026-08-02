from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_wizard_steps_use_native_keyboard_controls():
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")

    assert 'class="wizard-step-button"' in app_js
    assert 'aria-current="step"' in app_js
    assert '<nav class="wizard-progress-wrap" aria-label="Các bước khai báo">' in app_js
    assert "data-wizard-dot" in app_js


def test_local_draft_status_explains_storage_boundary():
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")

    assert 'id="draft-state"' in index_html
    assert 'role="status" aria-live="polite"' in index_html
    assert "Nháp cục bộ" in index_html
    assert "Nháp cục bộ · chưa gửi" in index_html
    assert "tanthuan-declaration-draft-saved-at" in app_js
    assert "function updateLocalDraftStatus(" in app_js


def test_inline_error_recovery():
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")

    assert "function showStepErrors(" in app_js
    assert "function showFieldError(" in app_js
    assert "function clearFieldError(" in app_js
    assert "step-error-summary" in app_js
    assert "aria-invalid" in app_js
    assert "field-error" in app_js
    assert "showFieldError(el," in app_js
    assert "function validateWizardForm(" in app_js
    assert "showStepErrors([error.message]" in app_js


def test_crew_checklist_replaces_select_multiple():
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")

    assert "function crewChecklistHtml(" in app_js
    assert "crew-checklist" in app_js
    assert 'type="checkbox"' in app_js
    assert 'name="crew_ids"' in app_js
    # declaration-crew-container is used instead of native select in wizard
    assert "declaration-crew-container" in app_js
    assert "crewContainer.querySelectorAll" in app_js
    assert "suggestion.crew_ids.includes(Number(input.value))" in app_js


def test_role_dashboard_layout():
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    assert "function roleLabel(role)" in app_js
    assert "const isCustomer = state.currentUser.role === 'CUSTOMER'" in app_js
    assert "const isAdmin = state.currentUser.role === 'PLATFORM_ADMIN'" in app_js
    assert "const isReviewer = state.currentUser.role === 'PORT_STAFF'" in app_js
    assert 'id="admin-operations"' in index_html
    assert 'id="integration-admin-actions"' in index_html
    assert "btn.hidden = !canCreateDeclaration" in app_js
    assert "$('#import-declaration-card').hidden = !(isReviewer || isAdmin)" in app_js
    assert "$('#admin-operations').hidden = true" in app_js
    assert "api('/api/admin/operations-summary')" not in app_js


def test_reporting_unit_picker_is_compact_and_kept_out_of_topbar():
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    styles_css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    sidebar_start = index_html.index('<aside class="sidebar"')
    sidebar_end = index_html.index('</aside>', sidebar_start)
    topbar_start = index_html.index('<header class="topbar"')
    topbar_end = index_html.index('</header>', topbar_start)
    assert 'id="reporting-unit-trigger"' in index_html[sidebar_start:sidebar_end]
    assert 'Chọn đơn vị báo cáo' not in index_html[sidebar_start:sidebar_end]
    assert 'id="reporting-unit-trigger"' not in index_html[topbar_start:topbar_end]
    assert 'id="reporting-unit-select"' not in index_html
    assert 'role="menuitemradio"' in app_js
    assert "event.key === 'Escape'" in app_js
    assert "['ArrowUp', 'ArrowDown']" in app_js
    assert '.reporting-unit-trigger' in styles_css
    assert '.reporting-unit-menu button.selected' in styles_css
    assert 'id="reporting-unit-dialog"' in index_html
    assert '+ Tạo đơn vị mới' in app_js
    assert 'Dành cho Platform Admin' not in app_js
    active_section = app_js[app_js.index("const active = state.reportingUnits.find"):app_js.index("if (!active)")]
    assert 'active.code' not in active_section
    assert "state.currentUser.role === 'PLATFORM_ADMIN'" in app_js
    assert "method: 'POST'" in app_js[app_js.index('async function saveReportingUnit'):app_js.index('async function loadReportingUnitContext')]


def test_crew_form_keeps_readable_controls_with_compact_two_column_layout():
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    styles_css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    assert "field('full_name','Họ và tên',item.full_name,'text','required')" in app_js
    assert '#crew-fields { grid-template-columns: repeat(2, minmax(0, 1fr)); }' in styles_css
    assert '#crew-fields label { gap: 4px; font-size: 10px; }' not in styles_css
    assert '#crew-fields input, #crew-fields select { min-height: 34px' not in styles_css


def test_terminology_standardized():
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    assert "Import dữ liệu" in app_js
    assert "Import dữ liệu" in index_html
    assert "Backup ngay" in index_html
    assert "NHẬP DỮ LIỆU CÓ KIỂM SOÁT" in index_html
    assert "Xác nhận import" in app_js
    assert '<p class="eyebrow">NHẬT KÝ</p>' in index_html
    assert "Dùng file mới · tạo bản sửa đổi" in app_js
    assert "<th>Bản sửa đổi</th>" in app_js
    assert 'data-label="Bản sửa đổi"' in app_js
    assert "tạo revision" not in index_html
    assert ">Revision<" not in app_js


def test_import_and_reports_tabs_are_platform_admin_only():
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    assert '<a href="#import" data-route="import" hidden>' in index_html
    assert '<a href="#reports" data-route="reports" hidden>' in index_html
    assert "importNav.hidden = !isAdmin" in app_js
    assert "reportsNav.hidden = !isAdmin" in app_js
    assert "const adminOnlyRoutes = ['import', 'reports'];" in app_js
    assert "state.currentUser.role !== 'PLATFORM_ADMIN' && adminOnlyRoutes.includes(name)" in app_js
    assert "state.currentUser.role === 'CUSTOMER' ? 'declarations' : 'dashboard'" in app_js
    assert "importNav.hidden = !(isReviewer || isAdmin)" not in app_js
    assert "reportsNav.hidden = isCustomer" not in app_js


def test_historical_import_is_visually_and_semantically_separate_from_live_import():
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    styles_css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    assert 'id="operational-import-tab"' in index_html
    assert 'id="historical-import-tab"' in index_html
    assert 'role="tabpanel" aria-labelledby="historical-import-tab"' in index_html
    assert "Không sửa phiếu khai báo gốc" in index_html
    assert 'id="import-historical" accept=".xlsx" multiple' in index_html
    assert 'id="historical-batch"' in index_html
    assert 'data-historical-row-filter="review"' in index_html
    assert 'id="historical-review-guide"' in index_html
    assert "Giữ bản đang dùng" in index_html
    assert "Dùng file mới · tạo bản sửa đổi" in app_js
    assert "function setImportMode(" in app_js
    assert "function previewHistoricalImport(" in app_js
    assert "function renderHistoricalBatch(" in app_js
    assert "function historicalWarnings(" in app_js
    assert "if (row.validationStatus === 'VALID') return [];" in app_js
    assert "function ensureHistoricalExportPanel(" in app_js
    assert "function exportHistoricalPl03(" in app_js
    assert "/api/historical-imports/reconcile" in app_js
    assert "Xác nhận Berth & ghép Detail" in app_js
    assert "PL.03 từ TOS" in app_js
    assert ">Xuất PL.03<" in app_js
    assert "ATB/ATD, TEU và tấn lấy từ Berth/Detail" not in app_js
    assert "function historicalEffectivePeriod(" in app_js
    assert "function renderHistoricalHistorySummary(" in app_js
    assert "Lý do / xử lý" in app_js
    assert "status=${status}" in app_js
    assert "function loadHistoricalImportHistory(" in app_js
    assert ".historical-import-steps" in styles_css
    assert "@media (max-width: 760px)" in styles_css


def test_vessel_editor_supports_profile_attachments():
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    styles_css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    assert "File đính kèm hồ sơ Salan" in app_js
    assert 'name="vessel_attachments" type="file" multiple' in app_js
    assert "function renderVesselAttachments(" in app_js
    assert "/attachments?filename=${encodeURIComponent(file.name)}" in app_js
    assert "data-delete-vessel-attachment" in app_js
    assert ".vessel-attachment-list" in styles_css


def test_vessel_editor_omits_blank_optional_fields_before_save_and_upload():
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    save_start = app_js.index("async function saveVessel(event)")
    save_end = app_js.index("function containerCountTons(", save_start)
    save_block = app_js[save_start:save_end]

    normalize = "Object.keys(data).forEach(key => { if (data[key] === '') delete data[key]; });"
    assert normalize in save_block
    assert save_block.index("data.organization = {name: data.organization_name};") < save_block.index(normalize)
    assert save_block.index(normalize) < save_block.index("saved = await api(path")
    assert save_block.index("saved = await api(path") < save_block.index("/attachments?filename=")
    assert '<script src="app.js?v=1.13.7" defer></script>' in index_html
    assert '<link rel="stylesheet" href="styles.css?v=1.13.7">' in index_html


def test_vessel_lists_show_accessible_attachment_indicator_only_when_files_exist():
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    styles_css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    assert "function vesselAttachmentIndicator(vessel, portRegister = false)" in app_js
    assert "const count = vessel.attachments?.length || 0;" in app_js
    assert "if (!count) return '';" in app_js
    assert 'type="button" class="vessel-attachment-indicator"' in app_js
    assert 'data-open-vessel-attachments="${vessel.id}"' in app_js
    assert 'aria-label="Mở ${label}"' in app_js
    assert 'width="14" height="14" style="width:14px;height:14px"' in app_js
    assert "${vesselAttachmentIndicator(v)}" in app_js
    assert "${vesselAttachmentIndicator(v, true)}" in app_js
    assert "function bindVesselAttachmentIndicators(root = document)" in app_js
    assert "async function openVesselAttachmentPreview(attachmentId)" in app_js
    assert "function downloadVesselAttachment(attachmentId, existingBlob = null)" in app_js
    assert "/attachments/${attachmentId}/download" in app_js
    assert "response.ok && responseType === 'blob'" in app_js
    assert "{responseType:'blob'}" in app_js
    assert 'class="vessel-attachment-preview-link"' in app_js
    assert 'data-preview-vessel-attachment="${item.id}"' in app_js
    assert "openVesselAttachmentPreview(Number(button.dataset.previewVesselAttachment))" in app_js
    assert "VESSEL_ATTACHMENT_IMAGE_EXTENSIONS" in app_js
    assert "sandbox></iframe>" in app_js
    assert "Word và Excel cần được tải xuống" in app_js
    assert "saveVesselAttachmentBlob(blob, attachment.original_name)" in app_js
    assert "URL.revokeObjectURL(state.vesselAttachmentPreview.objectUrl)" in app_js
    assert 'id="vessel-attachment-preview-dialog"' in index_html
    assert 'id="download-vessel-attachment">Tải xuống</button>' in index_html
    assert 'id="vessel-attachments-section"' in app_js
    assert ".vessel-name-with-attachment" in styles_css
    assert ".vessel-attachment-indicator svg" in styles_css
    assert ".vessel-attachment-preview-dialog" in styles_css
    assert '<script src="app.js?v=1.13.7" defer></script>' in index_html
    assert '<link rel="stylesheet" href="styles.css?v=1.13.7">' in index_html


def test_historical_cumulative_import_explains_sot_incremental_merge():
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")

    assert 'id="activate-historical-revision"' in index_html
    assert "Database đã xác nhận là Source of Truth" in app_js
    assert "sotRetainedCount" in app_js
    assert "newRowCount" in app_js
    assert "'MERGE_NEW_RECORDS'" in app_js
    assert "phát sinh mới" in app_js
    assert "'X-Reporting-Period': pl03PeriodValue()" in app_js


def test_report_dashboard_makes_source_coverage_and_overlap_explicit():
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    styles_css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    assert 'role="group" aria-label="Nguồn số liệu thống kê"' in index_html
    assert 'data-source="live" class="active"' in index_html
    assert 'data-source="historical"' in index_html
    assert 'data-source="combined"' in index_html
    assert 'id="analytics-coverage" class="analytics-coverage" aria-live="polite"' in index_html
    assert 'id="analytics-combined-blocked"' in index_html
    assert "const allowedSource = ['PORT_STAFF', 'PLATFORM_ADMIN'].includes" in app_js
    assert "data.combinedAllowed === false" in app_js
    assert "Chưa đủ độ phủ để tính" in app_js
    assert ".coverage-period.overlap" in styles_css
    assert "Chọn rõ nguồn trước khi đọc hoặc xuất tổng" not in index_html
    assert "Thống kê luôn ghi rõ nguồn" not in index_html
    assert "Tính từ TOS đã xác nhận" not in app_js


def test_wizard_step_order_customer_friendly():
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")

    # Verify B (Hành trình) appears before E (Thuyền trưởng) in DECLARATION_STEPS
    steps_start = app_js.index("const DECLARATION_STEPS")
    steps_end = app_js.index("];", steps_start)
    steps_section = app_js[steps_start:steps_end]

    idx_journey = steps_section.index("Hành trình")
    idx_crew = steps_section.index("Thuyền trưởng")
    assert idx_journey < idx_crew, (
        "Hành trình (B) phải đứng trước Thuyền trưởng (E) trong wizard steps"
    )


def test_preview_uses_customer_confirmation_language():
    preview_html = (ROOT / "frontend" / "preview.html").read_text(encoding="utf-8")

    assert "Kiểm tra trước khi xác nhận" in preview_html
    assert "Xác nhận & gửi" in preview_html
    assert "Khách hàng xác nhận gửi phiếu" in preview_html
    assert "Khách hàng nộp phiếu" not in preview_html
    assert "Khách hàng duyệt phiếu" not in preview_html


def test_data_navigation_stays_with_primary_navigation():
    styles_css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    assert ".data-nav { margin-top: 0; padding-top: 0; }" in styles_css
    assert ".data-nav { margin-top: auto;" not in styles_css
    assert ".sidebar-footer { margin-top: auto;" in styles_css
