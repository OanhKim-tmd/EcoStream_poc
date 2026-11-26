# Ghi chú phát hành và vận hành

Tài liệu này thay cho các hướng dẫn cũ có nội dung thương mại hóa, giá dịch vụ, số lượt miễn phí, mã license mẫu, thông tin thanh toán và tuyên bố bảo mật chưa được xác minh. Không dùng những nội dung cũ đó để cam kết với khách hàng.

## Trước khi cung cấp cho bên khác

1. Xác định chính xác phạm vi tính năng đang vận hành và giới hạn đã nêu trong [README.md](README.md).
2. Rà soát quy định kiểm kê KNK và biểu mẫu chính thức đang áp dụng; tài liệu trong `data/test_documents/` chỉ là tài liệu tham khảo lưu trong dự án.
3. Định nghĩa quy trình kiểm tra số liệu, hệ số, đơn vị, nguồn chứng cứ, người phê duyệt và truy vết thay đổi.
4. Thiết lập điều khoản xử lý dữ liệu, quyền truy cập, lưu trữ, sao lưu và xóa chứng từ; không sử dụng dữ liệu doanh nghiệp cho mục đích khác khi chưa có cơ sở/đồng ý phù hợp.
5. Nếu triển khai mạng, cấu hình secret `ECOSTREAM_API_KEY`, HTTPS, xác thực và phân quyền đầy đủ. API key đơn lẻ không tạo ra mô hình đa thuê bao an toàn.
6. Kiểm thử phiên bản phát hành với dữ liệu giả lập; ghi nhận các giới hạn trích xuất và lỗi đã biết.

## License, thanh toán và AI

Cơ chế bản quyền, gói Pro, watermark và webhook thanh toán **đã bị gỡ khỏi dự án** (phiên bản 0.3.0). Đã xóa `ecostream/privacy/licensing.py`, `scripts/generate_license_key.py`, `scripts/payment_webhook_server.py` và các endpoint `/api/auth/login`, `/api/license/verify`. Mọi chức năng đều miễn phí và không cần mã. Nếu sau này muốn thương mại hóa, cần thiết kế lại cơ chế cấp phép: không đưa secret ký vào mã nguồn, không dùng mã dùng thử công khai.

Ứng dụng không gửi dữ liệu tới dịch vụ AI bên ngoài và không có màn hình nhập khóa API: endpoint `/api/settings/ai` đã bị gỡ. Ứng dụng không dùng OCR; cách đọc chứng từ được mô tả ở mục "Cách EcoStream đọc chứng từ" trong [README.md](README.md).

## Xây dựng ứng dụng

Ứng dụng web chạy từ source bằng `python -m ecostream.app`; hướng dẫn đầy đủ tại [README.md](README.md). Cấu hình desktop và CI build có trong `scripts/`, `src-tauri/` và `.github/workflows/`. Cần xác minh artifact trên hệ điều hành đích trước khi phân phối.
