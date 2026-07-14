# Đánh giá lại UX trên Branch Recovery — 2026-07-13

Tài liệu này ghi nhận kết quả đánh giá lại các yêu cầu UX/UI của dự án sau khi hoàn thành các thay đổi trên branch `recovery`.

## Tóm tắt bối cảnh
- **Analytics — vẫn chờ tranche riêng.**
- **Kiểm thử trực quan đa viewport (2026-07-14):** Đã thu thập đầy đủ bằng chứng thực tế qua browser subagent. Kết quả kiểm thử **PASS** sau khi áp dụng các bản vá giao diện cho lỗi crash wizard, lỗi CSS leak panel tích hợp và co gọn icon sidebar mobile.

## Sổ trạng thái sau thi công

| Mã | Trạng thái hiện tại | Đã xử lý / kết luận | Còn thiếu hoặc cần chờ |
|---|---|---|---|
| UX-101 | **ĐÃ XỬ LÝ** | Font chữ đã được thống nhất sang "Inter", sans-serif trên toàn bộ ứng dụng; cỡ chữ tối thiểu 12px; khoảng cách dòng tối thiểu 1.5. | Đã xác nhận trực quan bằng mắt qua browser. |
| UX-102 | **ĐÍNH CHÍNH — ĐÃ CÓ SẴN** | Phân trang hoạt động khi gửi `page`; `page_size=2` trả đúng hai items và metadata tổng. Response mảng khi không có `page` là tương thích ngược có chủ ý. | Chỉ cần performance test với tập dữ liệu tham chiếu khi Gate 5 được tổ chức. |
| UX-103 | **ĐÃ XỬ LÝ** | Audit/runtime dùng “Khách hàng xác nhận gửi phiếu khai báo”; UI và preview bỏ “Nộp/nộp”. | Đã xác nhận trực quan bằng mắt qua browser. |
| UX-104 | **CHƯA ĐÓNG** | Dashboard đã ẩn chức năng theo role và có attention queue theo vai trò. | Chờ UAT thêm để xác định thứ tự ưu tiên widget; chưa đủ bằng chứng để tái cấu trúc dashboard. |
| UX-105 | **PASS** | Wizard có error summary, `aria-invalid`, mô tả lỗi theo field và focus về lỗi đầu tiên. Lỗi crash JS khi mở/tạo phiếu đã được khắc phục hoàn toàn. | Đã xác nhận trực quan bằng mắt qua browser. |
| UX-106 | **ĐÃ XỬ LÝ** | “Crew List” đã được Việt hóa trong app và preview. | Chỉ còn rà soát nội dung bằng mắt trong lượt browser/UAT. |
| UX-107 | **PASS** | Không còn role/stage CV/QLC/BP trong UI hay schema/runtime hiện hành; các tên action cũ chỉ còn trong deny-list và regression test để bảo đảm trả 410. | Không xóa deny-list/test vì đó là hàng rào chống client cũ gọi nhầm. |
| UX-002 cũ | **ĐÃ XỬ LÝ** | Nhãn được đổi thành “Nháp cục bộ · chưa gửi”, có thời điểm lưu cục bộ khi phát sinh. | Đã xác nhận trực quan bằng mắt qua browser. |
| UX-004 cũ | **PASS** | Native `select multiple` đã được thay bằng checkbox checklist thân thiện bàn phím/mobile. Đã sửa lỗi crash wizard để checklist hoạt động bình thường. | Đã xác nhận trực quan bằng mắt qua browser. |
| Analytics | **CHƯA XỬ LÝ — NGOÀI TRANCHE** | Đã xác nhận frontend gọi endpoint chưa tồn tại và xử lý 404 bằng toast, không làm vỡ trang. | Cần một tranche riêng gồm định nghĩa chỉ số, API contract, quyền truy cập, dữ liệu tham chiếu và thiết kế biểu đồ trước khi code. |
| Responsive/Gate 5 | **PASS** | Đã thu thập bằng chứng đa viewport thành công ngày 2026-07-14. Các lỗi layout, CSS và JS crash đã được sửa đổi và kiểm thử thành công trên Desktop, Laptop và Mobile. | Trạng thái Gate 5 sẵn sàng đóng. |
