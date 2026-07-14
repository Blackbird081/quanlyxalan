# Đánh giá lại UX trên Branch Recovery — 2026-07-13

## Tóm tắt bối cảnh
- **Analytics — vẫn chờ tranche riêng.**
- **Kiểm thử trực quan đa viewport (2026-07-14):** Đã thu thập đầy đủ bằng chứng thực tế qua browser automation/Playwright. Kết quả kiểm thử **PASS** cho toàn bộ 6 bước của wizard tạo phiếu.

## Sổ trạng thái sau thi công

| Mã | Trạng thái hiện tại | Đã xử lý / kết luận |
|---|---|---|
| UX-101 | **ĐÃ XỬ LÝ** | Font chữ đã được thống nhất sang "Inter", sans-serif trên toàn bộ ứng dụng; cỡ chữ tối thiểu 12px; khoảng cách dòng tối thiểu 1.5. |
| UX-102 | **ĐÍNH CHÍNH — ĐÃ CÓ SẴN** | Phân trang hoạt động khi gửi `page`; `page_size=2` trả đúng hai items và metadata tổng. |
| UX-103 | **ĐÃ XỬ LÝ** | Audit/runtime dùng “Khách hàng xác nhận gửi phiếu khai báo”; UI và preview bỏ “Nộp/nộp”. |
| UX-105 | **PASS** | Wizard có error summary, `aria-invalid`, mô tả lỗi và focus về lỗi đầu tiên. Lỗi crash JS đã khắc phục triệt để. |
| UX-106 | **ĐÃ XỬ LÝ** | “Crew List” đã được Việt hóa trong app và preview. |
| UX-107 | **PASS** | Không còn role/stage CV/QLC/BP trong UI hay schema/runtime. |
| UX-002 cũ | **ĐÃ XỬ LÝ** | Nhãn được đổi thành “Nháp cục bộ · chưa gửi”, có thời điểm lưu cục bộ khi phát sinh. |
| UX-004 cũ | **PASS** | Native `select multiple` đã được thay bằng checkbox checklist thân thiện bàn phím/mobile. |
| Responsive/Gate 5 | **PASS** | Đã thu thập bằng chứng đa viewport thành công ngày 2026-07-14. Các lỗi layout, CSS và JS crash đã được sửa đổi và kiểm thử thành công trên Desktop, Laptop và Mobile. |
