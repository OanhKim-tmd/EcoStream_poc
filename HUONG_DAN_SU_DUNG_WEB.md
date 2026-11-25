# Hướng dẫn sử dụng EcoStream Web

Hướng dẫn này mô tả luồng khảo sát hiện hành. Phạm vi tự động hóa còn giới hạn; người dùng cần kiểm tra mọi dữ liệu trước khi tính và sử dụng kết quả. Xem [README.md](README.md) để biết phạm vi, cài đặt và danh mục tài liệu nguồn.

## 1. Khởi chạy

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m ecostream.app
```

Mở địa chỉ được in ra khi máy chủ khởi động, thông thường `http://127.0.0.1:8000/`. Dùng `Ctrl+C` để dừng. Các trang chính:

- `/` — giao diện tải chứng từ, rà soát biểu và kết quả.
- `/docs` — tài liệu API của luồng khảo sát.

Trang `/monitor` dành cho phát triển/debug pipeline cũ, không cần thiết cho người dùng app.

Ứng dụng **không có tài khoản, gói Pro hay mã bản quyền**: mọi chức năng và tệp kết quả đều dùng được ngay. Sau khi cài đặt, ứng dụng chạy **hoàn toàn không cần Internet** (CSS và phông chữ lưu sẵn trong máy).

Trong môi trường phát triển, API không yêu cầu khóa nếu chưa đặt `ECOSTREAM_API_KEY`. Khi cấu hình biến này, gửi khóa qua header `X-API-Key`. Không triển khai công khai nếu chưa bổ sung xác thực người dùng, phân quyền, HTTPS và biện pháp bảo vệ dữ liệu phù hợp.

## 2. Tạo biểu khảo sát

1. Trên giao diện, chọn/tải một hoặc nhiều chứng từ.
2. Điền tên doanh nghiệp, cơ sở, năm báo cáo và các thông tin chung nếu có.
3. Bắt đầu tạo khảo sát.
4. Xem danh sách tệp được dùng/chưa dùng, các cảnh báo và những ô dữ liệu đã nhận dạng.
5. Tải hoặc rà soát biểu Excel. Bổ sung thủ công nội dung còn thiếu; không xem ô trống là số 0.

API hiện giới hạn tối đa 100 tệp, mỗi tệp tối đa 10 MB; chỉ nhận `.xlsx`, `.csv`, `.pdf`, `.docx`. Ảnh bị từ chối. PDF phải **có lớp chữ** (hóa đơn điện tử, bản xuất từ phần mềm); với PDF scan, ứng dụng cảnh báo và bạn nhập số liệu thủ công. Tệp có thể không được trích xuất tự động dù được upload thành công. Kết quả trích xuất luôn cần được đối chiếu với chứng từ gốc.

## 3. Tính toán và tải kết quả

Sau khi rà soát biểu khảo sát:

1. Bấm tính toán từ giao diện, hoặc gửi lại workbook đã sửa nếu giao diện cho phép.
2. Kiểm tra cảnh báo/trạng thái hoàn tất.
3. Tải các đầu ra của phiên:
   - `Bang_khao_sat_da_dien.xlsx`
   - `GHGs_inventory_da_tinh.xlsx`
   - `Bao_cao_kiem_ke_KNK.docx`

Ba tệp trên là toàn bộ đầu ra của luồng khảo sát; không có bản HTML/PDF riêng. Đầu ra là bản hỗ trợ/dự thảo.

Nếu biểu khảo sát có sinh khối, chất thải, than bùn, LNG, dầu hỏa hoặc sản phẩm dầu mỏ khác, các dòng này **không được cộng vào tổng** và được ghi "CHƯA TÍNH" trong cảnh báo. Lý do: EcoStream chưa có hệ số phát thải riêng cho chúng (xem README). Hãy đối chiếu các giá trị với chứng từ gốc, công thức workbook, hệ số và hướng dẫn hiện hành. Không dùng làm hồ sơ đã được thẩm định.

## 4. Dữ liệu demo

Dữ liệu trong `data/demo_full_2026/` được gắn nhãn giả lập. Xem `data/demo_full_2026/README.txt` để biết file nào cần tải, các giá trị dùng để kiểm tra và các nguồn chưa được tính. Đây không phải chứng từ thật, không có giá trị pháp lý và không dùng làm kết quả đã thẩm định.

## 5. Lưu trữ và riêng tư

Mỗi phiên được ghi trong `runs/<run_id>/`, gồm chứng từ đã tải và tệp kết quả. Thư mục này có thể chứa dữ liệu nhạy cảm. Giới hạn quyền truy cập, sao lưu theo chính sách nội bộ và xóa theo thời hạn lưu trữ của đơn vị. Không đưa dữ liệu thật lên máy chủ công khai chưa được bảo vệ.

## 6. Giới hạn

- Tự trích xuất chỉ hỗ trợ một số cấu trúc bảng và loại dữ liệu; cần rà soát thủ công.
- Luồng khảo sát tính phần nguồn Scope 1/2 được ánh xạ; không giả định mọi nguồn hoặc mọi sheet đều được hỗ trợ.
- Không tự nội suy tháng bị thiếu hoặc tự suy đoán số liệu giảm nhẹ/hạn ngạch.
- Không có OCR: ảnh không được nhận, PDF scan phải nhập thủ công.
- Chỉ nhiên liệu có hệ số riêng mới được tính; các nhiên liệu khác được giữ trong biểu nhưng ghi "CHƯA TÍNH".
- Tài liệu tham khảo pháp lý nằm trong `data/test_documents/`; kiểm tra văn bản đang có hiệu lực và hướng dẫn chính thức trước khi lập hồ sơ.

## API khảo sát chính

- `POST /api/survey/prepare` — nhận chứng từ và thông tin cơ sở.
- `GET /api/survey/runs/{run_id}/survey/preview` — xem trước biểu.
- `GET /api/survey/runs/{run_id}/survey/data` và `POST /api/survey/runs/{run_id}/survey/save` — đọc/lưu dữ liệu biểu.
- `POST /api/survey/runs/{run_id}/calculate` — tính từ biểu khảo sát.
- `GET /api/survey/runs/{run_id}/files/{kind}` — tải `survey`, `inventory` hoặc `report`.
