# 🌱 Hướng Dẫn Chạy Local Web & Sử Dụng Hệ Thống EcoStream

Tài liệu này hướng dẫn chi tiết cách khởi chạy máy chủ Web cục bộ (Local Web), cách thao tác tính toán kiểm kê khí nhà kính (KNK) trên giao diện và cách tra cứu, đối soát các thông tin kết quả cũng như dữ liệu trung gian của hệ thống **EcoStream**.

---

## 1. Cách Chạy Local Web

### Bước 1: Chuẩn bị môi trường
Đảm bảo máy tính đã cài đặt **Python 3.10+** và đang mở Terminal / PowerShell tại thư mục gốc của dự án (`EcoStream`).

```powershell
# (Tùy chọn) Kích hoạt môi trường ảo nếu có
.\.venv\Scripts\Activate.ps1

# Cài đặt đầy đủ các thư viện phụ thuộc
pip install -r requirements.txt
```

### Bước 2: Khởi động máy chủ Web
Bạn có thể khởi chạy máy chủ bằng một trong các lệnh sau:

**Cách 1 — Chạy qua module ứng dụng (Khuyên dùng):**
```powershell
python -m ecostream.app
```
*(Hệ thống sẽ tự động tìm cổng trống bắt đầu từ `8000`, mặc định là `http://127.0.0.1:8000`).*

**Cách 2 — Chạy trực tiếp file server:**
```powershell
python ecostream/app/server.py
```

**Cách 3 — Chạy bằng Uvicorn (hỗ trợ tự động tải lại khi sửa code):**
```powershell
uvicorn ecostream.app.server:app --host 127.0.0.1 --port 8000 --reload
```

### Bước 3: Truy cập trên trình duyệt
Sau khi màn hình hiển thị thông báo:
> `[EcoStream] Multi-Agent Web Server is live at: http://127.0.0.1:8000`

Hãy mở trình duyệt (Chrome, Edge, Firefox...) và truy cập các đường dẫn sau:

| Trang | Đường dẫn (URL) | Chức năng chính |
| :--- | :--- | :--- |
| **Bảng Điều Khiển Chính** | `http://127.0.0.1:8000/` | Tải chứng từ, chạy tính toán phát thải CO₂e, xem tổng quan KPI và tải báo cáo. |
| **Live Workflow Monitor** | `http://127.0.0.1:8000/monitor` | Giám sát tiến trình đa tác tử thời gian thực, thanh tra dữ liệu bóc tách & nhật ký kiểm toán. |
| **Tài liệu API (Swagger UI)** | `http://127.0.0.1:8000/docs` | Giao diện thử nghiệm và tra cứu trực tiếp các REST API của hệ thống. |

> **Lưu ý về Bảo mật / API Key (Tùy chọn):**
> Mặc định ở chế độ phát triển cục bộ (`development_unrestricted`), hệ thống **không yêu cầu mật khẩu hay API Key**. Nếu bạn thiết lập biến môi trường `ECOSTREAM_API_KEY`, mọi yêu cầu gọi API cần đính kèm header `X-API-Key` hoặc tham số `?api_key=...`.

---

## Bộ dữ liệu giả lập đa định dạng (năm 2026)

Từ thư mục dự án chạy `python scripts/generate_survey_demo.py` để tạo bốn tệp giả lập trong `data/demo_full_2026/`: `fuel_stationary.xlsx`, `fuel_mobile.docx`, `electricity_months_02_12.csv`, `electricity_month_01.pdf`. Tất cả có nhãn **DỮ LIỆU GIẢ LẬP — KHÔNG CÓ GIÁ TRỊ PHÁP LÝ**. Tải đồng thời cả bốn tệp lên giao diện, nhập kỳ 2026. Điện đủ 12 tháng; bảng nhiên liệu cố định/di động có dòng theo tháng. Mở biểu khảo sát để đối chiếu trước khi bấm tính. Đọc `data/demo_full_2026/README.txt` để xem các mục chưa hỗ trợ. **Bộ này chỉ phủ nguồn đang tính được, chưa thể điền mọi sheet hoặc mọi ô của hai mẫu**; không dùng làm chứng từ thật.

| Nhóm dữ liệu từ chứng từ | Biểu khảo sát | Workbook kiểm kê | Tình trạng |
| --- | --- | --- | --- |
| Diesel, than bitum, LPG đốt cố định | `1.1`, F:Q theo tháng | `S1-Stationary Combustion`, D:O | Trích xuất, xuất biểu, tính theo EF EcoStream; kiểm tra chênh lệch với phương pháp TJ của mẫu. |
| Xăng và diesel phương tiện | `1.2`, F:Q theo tháng | `S1-Mobile Combustion`, D:O | Trích xuất, xuất biểu và tính; cần xác nhận tỷ trọng/hệ số TJ của mẫu. |
| Điện mua lưới | `2.1`, E3:E14 | `S2-Electricity Consumption`, C7:C18 | Đủ 12 tháng từ CSV/PDF giả lập; EF EcoStream 2023 cần xác nhận cho kỳ 2026. |
| Khai khoáng | `1.3` và biểu thông tin khai khoáng có cột năm 2020/2022 | Chưa xác lập ánh xạ phát thải | Chưa có phương pháp phát tán và dữ liệu đặc thù; không điền khống. |
| Môi chất lạnh | `1.4`, F:Q theo tháng | `S1-Refrigerants` | Chưa xác minh chất/GWP và lượng rò rỉ thực tế; lượng nạp không mặc nhiên bằng lượng phát thải. |
| Quá trình công nghiệp | `1.5`, F:Q theo tháng | `S1-Industrial processes` | Chưa xác lập quy trình, hàm lượng nguyên liệu và hệ số; để trống. |
| Nước thải | `1.6`, thể tích và COD theo tháng | `S1-Wastewater Treatment` | Thiếu thông số/phương pháp CH₄, N₂O của công nghệ xử lý; để trống. |
| Điện tự sản xuất/tự dùng; hơi mua | `2.1` cột F; `2.2` khối lượng hơi và điều kiện vận hành | Không có ánh xạ tính riêng đã kiểm chứng | Không cộng vào điện mua; không tự suy ra EF hơi. |
| Biện pháp giảm thiểu | `Biện pháp giảm thiểu` | Không đủ PTCS/PT và xác minh | Chỉ ghi khi có bằng chứng; không tự tính mức giảm hoặc hạn ngạch. |

Đối chiếu nhanh file demo sau khi tải: `1.1!F8=1010` lít diesel; `1.2!F4=282` lít xăng; `2.1!E3=30500` và `E9=33500` kWh. Workbook kiểm kê tương ứng có `S2-Electricity Consumption!C7=30500`, `C13=33500`; tổng điện mua là **399000 kWh**. Các con số này là dữ liệu hoạt động giả lập, không phải số phát thải đã được thẩm định.

## 2. Luồng khảo sát → kiểm kê → một báo cáo Word (Scope 1/2)

1. Chạy `python -m ecostream.app`, mở `http://127.0.0.1:8000/`. Chọn tối đa 20 chứng từ `.xlsx`, `.csv`, `.pdf`, `.docx` (mỗi tệp không quá 10 MB), nhập doanh nghiệp, cơ sở và năm rồi tạo khảo sát.
2. Xem danh sách tệp **đã dùng/chưa dùng**, bảng dòng có vị trí nguồn, cảnh báo và bản xem để in. Tải `Bang_khao_sat_da_dien.xlsx` để mở trong Excel. Các tháng chưa có chứng từ vẫn để trống; không nội suy. Có thể sửa file và nộp bản `.xlsx` đã sửa khi tính, nhưng không bắt buộc.
3. Bấm tính từ biểu khảo sát. Tải `GHGs_inventory_da_tinh.xlsx` và `Bao_cao_kiem_ke_KNK.docx` trong cùng phiên. Sheet **EcoStream đối soát** ghi tổng theo hệ số EcoStream; các sheet gốc của mẫu kiểm kê sử dụng phương pháp nhiệt trị và hệ số từng khí khác nên không được coi là đã khớp số, phải rà soát trên phần mềm bảng tính có tính lại công thức.
4. Bản Word là **dự thảo đối soát**, chỉ gồm Scope 1/2 có dữ liệu. Nếu thiếu PTCS, PT, phương pháp giám sát và bằng chứng, không tính giảm nhẹ/hạn ngạch. Không dùng hồ sơ này như hồ sơ kiểm kê đã thẩm tra.

Hiện việc tự trích xuất chỉ nhận những dòng bảng có tháng, số lượng và đơn vị theo cấu trúc được hỗ trợ; hóa đơn PDF hoặc chứng từ bố cục khác có thể cần nhập thủ công trên biểu khảo sát. Hệ số EcoStream đang mang niên độ 2023, cần kiểm tra sự phù hợp với năm kiểm kê. Khi cấu hình `ECOSTREAM_API_KEY`, API yêu cầu header `X-API-Key`; giao diện cần tích hợp xác thực phù hợp trước khi triển khai công khai. Không cung cấp chứng từ nhạy cảm trên máy chủ mở mà chưa có cơ chế phân quyền.

API: `POST /api/survey/prepare` (`files`, `company`, `location`, `period`), `GET /api/survey/runs/{run_id}/survey/preview`, `POST /api/survey/runs/{run_id}/calculate` (tùy chọn `reviewed`), `GET /api/survey/runs/{run_id}/files/{survey|inventory|report}`.

### Hướng dẫn cho giao diện cũ

Phần bên dưới mô tả pipeline `/api/upload` trước đây. Nó vẫn tồn tại cho các client cũ, nhưng **không phải** luồng khảo sát–kiểm kê mới. Đặc biệt các mô tả “95% CI”, tự nội suy và Mẫu 02 bên dưới không áp dụng cho luồng mới.

## 2. Hướng Dẫn Sử Dụng Giao Diện Web Chính (`/`)

Khi truy cập trang chủ `http://127.0.0.1:8000/`, bạn có **2 cách** để thực hiện kiểm kê khí nhà kính:

### Cách 1: Chạy thử nhanh với Dữ liệu Mẫu (Benchmark Demo)
Dành cho việc trải nghiệm nhanh luồng hoạt động của hệ thống mà chưa cần chuẩn bị file:
1. Nhấn vào nút **"⚡ Thử Dữ Liệu Mẫu"** ở góc trên bên phải thanh tiêu đề.
2. Hệ thống sẽ tự động nạp bộ hồ sơ mẫu (`data/samples/input.xlsx`) của doanh nghiệp giả định **EcoGarment Vietnam JSC — Nhà máy May & Năng lượng Hà Nam**.
3. Sau vài giây xử lý, màn hình kết quả kiểm kê và các nút tải báo cáo sẽ hiển thị đầy đủ.

### Cách 2: Tải lên Chứng từ Thực tế của Doanh nghiệp
1. **Đính kèm tệp chứng từ**:
   - Kéo & thả các tệp vào khung nét đứt **"Kéo & Thả chứng từ vào đây"** hoặc bấm vào khung để chọn tệp từ máy tính.
   - **Định dạng hỗ trợ**: Hóa đơn tiền điện EVN (`.pdf`), bảng kê nhiên liệu/vận tải Excel (`.xlsx`, `.xls`, `.csv`), biên bản/chứng từ Word (`.docx`).
   - Có thể chọn **nhiều tệp cùng lúc**. Để bỏ bớt tệp đã chọn, nhấn nút `✕` màu đỏ cạnh tên tệp.
2. **Điền thông tin định danh cơ sở (3 trường bắt buộc)**:
   - **Tên Doanh Nghiệp**: Ví dụ `Công ty Cổ phần Dệt May Xanh`.
   - **Cơ Sở / Nhà Máy**: Ví dụ `Nhà máy Sản xuất Hà Nam`.
   - **Kỳ Báo Cáo**: Năm thực hiện kiểm kê, ví dụ `2026`.
3. **Bắt đầu tính toán**:
   - Nhấn nút **"🚀 Bắt Đầu Tính Toán & Xuất Báo Cáo"**.
   - Chờ hệ thống chuyển đổi chứng từ, bóc tách số liệu qua các tác tử AI (Subagents) và tính toán phát thải theo hệ số MONRE / IPCC.
4. **Tính toán lượt mới**:
   - Khi muốn quay lại màn hình tải tệp để chạy cho bộ hồ sơ khác, nhấn nút **"↺ Tính Toán Lượt Mới"** ở góc phải phần kết quả.

---

## 3. Cách Xem Các Thông Tin & Đọc Kết Quả

Hệ thống cung cấp thông tin theo 2 cấp độ: **Tổng quan & Báo cáo hoàn chỉnh** (trên trang chủ `/`) và **Chi tiết chuyên sâu từng bước xử lý** (trên trang `/monitor`).

### 3.1. Xem kết quả trên Bảng Điều Khiển Chính (`http://127.0.0.1:8000/`)

Sau khi quá trình tính toán hoàn tất, màn hình sẽ hiển thị 3 khu vực thông tin chính:

#### A. 4 Thẻ Chỉ Số Cốt Lõi (KPI Cards)
1. **Tổng Phát Thải Ròng (`tCO₂e`)**:
   - Tổng lượng phát thải khí nhà kính quy đổi ra tấn CO₂ tương đương.
   - Đi kèm **Khoảng tin cậy `95% CI`** (ví dụ: `95% CI: [4,454.7 - 5,435.4] t`) được tính bằng phương pháp lan truyền sai số Gaussian.
2. **Scope 1 (Phát thải Trực tiếp - `tCO₂e`)**:
   - Phát thải từ việc đốt nhiên liệu trực tiếp tại cơ sở như: Than đá, dầu DO/FO lò hơi, xăng/dầu chạy xe nội bộ, khí gas LPG.
3. **Scope 2 (Phát thải Gián tiếp - `tCO₂e`)**:
   - Phát thải từ tiêu thụ điện năng mua ngoài lưới điện quốc gia (EVN), áp dụng hệ số phát thải lưới điện Việt Nam của Bộ TN&MT (MONRE).
4. **Độ Tin Cậy Dữ Liệu (Reliability Score & Grade)**:
   - Hiển thị tỷ lệ phần trăm độ tin cậy tổng hợp (ví dụ: `88.5%`) và xếp hạng **`GRADE A` / `B` / `C`** dựa trên chất lượng chứng từ gốc, phương pháp đo đạc và mức độ đầy đủ của dữ liệu.

#### B. Tải Về Trọn Bộ Báo Cáo Quy Chuẩn (Download Hub)
Ngay bên dưới các thẻ số liệu là 4 nút xuất hồ sơ trực tiếp:
- **🌐 Báo Cáo HTML (`/api/report/html`)**: Mở trong tab mới, trình bày trực quan, hỗ trợ in ấn nhanh (`Ctrl + P`).
- **📝 Word Mẫu 02 (`/api/report/docx`)**: Tải về file `Bao_cao_Mau02_ND06.docx` được định dạng theo **Mẫu số 02 Phụ lục IV — Nghị định 06/2022/NĐ-CP**, thuận tiện để chỉnh sửa, đóng dấu và nộp cơ quan quản lý.
- **📕 Báo Cáo PDF (`/api/report/pdf`)**: Tải/xem file `Bao_cao_kiem_ke_va_giam_nhe_KNK.pdf` cố định bố cục, phục vụ lưu trữ và ký duyệt kiểm toán độc lập.
- **📊 Hồ Sơ Excel (`/api/report/excel`)**: Tải về file `Ho_so_ket_qua_CO2_EcoStream.xlsx` chứa bảng tính chi tiết từng dòng hoạt động để kế toán/kiểm toán viên đối soát.

#### C. Bảng Danh Sách Hoạt Động & Bằng Chứng Bóc Tách
Nhấn vào thanh **"📋 Danh Sách Hoạt Động & Bằng Chứng Bóc Tách (▼ Xem chi tiết)"** ở cuối thẻ kết quả để mở rộng bảng đối chiếu từng nguồn phát thải:
- **Mô tả hoạt động**: Tên nhiên liệu, thiết bị hoặc kỳ hóa đơn điện.
- **Scope**: Phân loại `Scope 1` hoặc `Scope 2`.
- **Lượng hoạt động**: Số lượng tiêu thụ thực tế kèm đơn vị chuẩn hóa (`kg`, `L`, `kWh`...).
- **Hệ số EF**: Hệ số phát thải được áp dụng.
- **Phát thải (`tCO₂e`)**: Kết quả nhân tất định $E = Q \times EF$.
- **Chứng từ gốc**: Tên file hoặc sheet gốc nơi số liệu được trích xuất (Audit Trail).
- **Độ tin cậy**: Điểm chất lượng dữ liệu của riêng dòng hoạt động đó (`%`).

---

### 3.2. Xem chi tiết tiến trình & dữ liệu trung gian trên Live Monitor (`http://127.0.0.1:8000/monitor`)

Trang **Live Workflow Monitor** dành cho kỹ thuật viên, kiểm toán viên hoặc người dùng muốn kiểm tra sâu bên trong "hộp đen" của các tác tử AI:

#### A. Chọn Phiên Chạy & Điều Khiển Quét Tự Động (Run Selector)
- **Danh Sách Phiên Đã Lưu**: Chọn một phiên chạy bất kỳ từ menu thả xuống (ví dụ: `EcoGarment-Vietnam-JSC_...` hoặc `run_2026...`), hoặc nhập trực tiếp mã `run_id` vào ô tìm kiếm.
- **Chu kỳ quét & Tự động quét**: Mặc định giao diện tự động cập nhật dữ liệu mỗi **3 giây**. Bạn có thể đổi sang `1s`, `2s`, `5s`, `10s`, tạm dừng (`⏸`) hoặc nhấn **"🔄 Làm Mới Ngay"**.

#### B. Theo Dõi Vòng Đời 5 Bước (5-Phase Lifecycle Stepper)
Hiển thị tiến độ phần trăm (`0% -> 100%`) và trạng thái của 5 giai đoạn:
1. **Bước 1 — Ingestion**: Chuyển đổi file sang Markdown bằng MarkItDown & kiểm tra bộ nhớ đệm SHA-256.
2. **Bước 2 — Schema Discovery**: Phân tích cấu trúc tài liệu và lập danh mục định tuyến (`index.json`).
3. **Bước 3 — Domain Subagents**: Trạng thái hoạt động và số mục trích xuất của 4 tác tử chuyên biệt (`Scope1FuelAgent`, `Scope2PowerAgent`, `Scope3SupplyAgent`, `MitigationQuotaAgent`).
4. **Bước 4 — Deterministic Math**: Tính toán phát thải tất định, khoảng tin cậy 95% CI và cân đối hạn ngạch.
5. **Bước 5 — Synthesis & Mẫu 02**: Tổng hợp báo cáo và xuất bản tài liệu.

#### C. Thanh Tra Tệp Trung Gian (Intermediate Blackboard Inspector)
Khu vực bên dưới cung cấp các tab chuyên biệt để bạn tra cứu toàn bộ dữ liệu trung gian trong thư mục `runs/<run_id>/`:
- **📊 Trạng Thái & Định Tuyến**: Xem thông tin thời gian bắt đầu/kết thúc (`state.json`) và cách hệ thống phân luồng từng sheet/tệp cho từng Agent (`index.json`).
- **🔥 Scope 1 (Nhiên Liệu)**: Xem bảng dữ liệu nhiên liệu đốt, đối chiếu giữa *Số lượng gốc / Đơn vị gốc* (ví dụ: bình LPG 45kg) và *Số lượng quy đổi chuẩn* (`kg`, `L`, `m³`), hoặc tải file `scope1_extracted.json`.
- **⚡ Scope 2 (Điện EVN)**: Xem sản lượng điện từng tháng (`kWh`), mã khách hàng/đồng hồ, và phát hiện các tháng bị thiếu hóa đơn được gắn nhãn **`⚠️ Nội suy (Interpolated)`**.
- **⚠️ Nhật Ký & Giả Định (Audit Logs)**:
  1. **Nhật Ký Truy Vấn Bất Thường (`Query Log`)**: Liệt kê các điểm dữ liệu nghi vấn, thiếu hụt hoặc bất thường cần con người xác nhận lại, kèm hành động khắc phục tạm thời của hệ thống.
  2. **Nhật Ký Giả Định (`Assumption Log`)**: Ghi rõ các quy chuẩn/giả định bảo thủ đã áp dụng (như nội suy tuyến tính theo mùa, khối lượng riêng nhiên liệu), mức **Trừ điểm tin cậy (`-%`)** và mức **Tăng độ bất định (`+%`)**.
- **📄 Trình Xem File Gốc (Raw JSON)**: Cho phép chọn và đọc trực tiếp nội dung JSON thô của bất kỳ tệp nào (`state.json`, `index.json`, `math_results.json`, `query_log.json`, `assumption_log.json`...) và sao chép nhanh vào Clipboard.

---

### 3.3. Xem trực tiếp trong Thư mục Dự án (`runs/`)

Ngoài giao diện Web, mọi kết quả của mỗi lần chạy đều được lưu trữ bền vững trên ổ cứng tại thư mục `runs/<run_id>/`:
- `runs/<run_id>/state.json` & `index.json`: Trạng thái và chỉ mục định tuyến.
- `runs/<run_id>/inputs/`: Các bản Markdown đã được chuẩn hóa từ chứng từ gốc.
- `runs/<run_id>/intermediate/`: Toàn bộ các file JSON trích xuất trung gian và nhật ký kiểm toán (`query_log.json`, `assumption_log.json`, `math_results.json`).
- `runs/<run_id>/deliverables/`: Chứa các báo cáo hoàn chỉnh (`.md`, `.html`, `.docx`, `.pdf`, `final_inventory_summary.json`).
