# 💸 Hướng Dẫn Deploy EcoStream Miễn Phí 100% (\$0/tháng)

Để tối ưu chi phí ở mức **\$0 (Miễn phí hoàn toàn)** nhưng vẫn có đường dẫn Web toàn cầu (`https://...`) gửi cho khách hàng doanh nghiệp trải nghiệm hoặc đóng gói bán trực tiếp, dưới đây là **3 phương án tối ưu nhất** đã được cấu hình sẵn trong dự án.

---

## 📊 So Sánh 3 Phương Án Deploy Miễn Phí

| Tiêu chí | 1. Hugging Face Spaces (Docker) ⭐ **Khuyên dùng số 1** | 2. Render.com (Free Web Service) | 3. Đóng gói Desktop `.exe` (Offline Local) |
| :--- | :--- | :--- | :--- |
| **Chi phí** | **\$0 / tháng** (Không cần thẻ Visa) | **\$0 / tháng** (750 giờ/tháng) | **\$0 / tháng** (Chạy trên máy khách hàng) |
| **Cấu hình miễn phí** | **16 GB RAM • 2 vCPU** (Cực mạnh) | **512 MB RAM • 0.1 CPU** | Dùng cấu hình máy tính của khách hàng |
| **Hỗ trợ OCR PDF tiếng Việt** | ✅ Có sẵn (`Tesseract` + `Poppler` trong `Dockerfile`) | ✅ Có sẵn (Chạy qua `Dockerfile`) | ✅ Chạy trực tiếp trên Windows |
| **Tên miền (URL)** | `https://<user>-ecostream.hf.space` | `https://ecostream-ai-carbon.onrender.com` | `http://127.0.0.1:8000` (Tự mở trình duyệt) |
| **Thời gian ngủ (Cold Start)** | Ngủ sau 48h không ai vào | Ngủ sau 15 phút không ai vào | Khởi động tức thì (1 giây) |

---

## Phương Án 1: Deploy Lên Hugging Face Spaces (Free 16GB RAM — Tốt Nhất)

Tại sao nên chọn **Hugging Face Spaces**?
Các nền tảng như Render hay Fly.io bản Free chỉ cho **512MB RAM**, rất dễ bị tràn bộ nhớ khi doanh nghiệp tải lên file PDF scan hoặc Excel lớn. Riêng **Hugging Face Spaces (chế độ Docker)** tặng miễn phí **16GB RAM và 2 CPU**, chạy mượt toàn bộ pipeline Multi-Agent, `MarkItDown` và `Tesseract OCR`.

### Các bước thực hiện (5 phút):
1. Truy cập [https://huggingface.co/spaces](https://huggingface.co/spaces) và đăng ký/đăng nhập tài khoản miễn phí.
2. Nhấn nút **"Create new Space"**:
   - **Space name**: `ecostream`
   - **Select the Space SDK**: Chọn **Docker** $\to$ chọn mẫu **Blank**.
   - **Space Hardware**: Chọn **CPU basic (2 vCPU · 16 GB · FREE)**.
   - **Visibility**: Chọn **Public** $\to$ nhấn **Create Space**.
3. Đẩy code từ máy tính của bạn lên Hugging Face Space vừa tạo:
   ```powershell
   # Thêm remote tới Hugging Face Space của bạn (thay <USERNAME> bằng tên tài khoản HF)
   git remote add hf https://huggingface.co/spaces/<USERNAME>/ecostream

   # Đẩy nhánh web_demo lên nhánh main của Hugging Face Space
   git push hf web_demo:main --force
   ```
4. Đợi khoảng 2–3 phút để Hugging Face tự động build [`Dockerfile`](file:///d:/Workspace/EcoStream/Dockerfile). Khi trạng thái chuyển sang **`Running`**, bạn sẽ có đường dẫn Web toàn cầu:
   - **Link trực tiếp**: `https://<USERNAME>-ecostream.hf.space`
   - **Link Live Monitor**: `https://<USERNAME>-ecostream.hf.space/monitor`

---

## Phương Án 2: Deploy Tự Động Từ GitHub Lên Render.com (\$0/tháng)

Dự án đã có sẵn file cấu hình [`render.yaml`](file:///d:/Workspace/EcoStream/render.yaml) và [`Dockerfile`](file:///d:/Workspace/EcoStream/Dockerfile).

### Các bước thực hiện:
1. Truy cập [https://render.com](https://render.com) và đăng nhập bằng tài khoản **GitHub** của bạn.
2. Trên Dashboard của Render, nhấn **"New +"** $\to$ chọn **"Web Service"**.
3. Chọn kết nối tới repository **`OanhKim-tmd/EcoStream_poc`**.
4. Thiết lập cấu hình:
   - **Branch**: `web_demo`
   - **Runtime**: `Docker`
   - **Instance Type**: Chọn **Free (\$0/month)**
5. Nhấn **"Create Web Service"**. Render sẽ tự động cài đặt và cấp cho bạn địa chỉ `https://ecostream-ai-carbon.onrender.com`.

> **Mẹo chống ngủ (Keep-Alive) cho Render Free**:
> Bản Free của Render sẽ tự nghỉ sau 15 phút không có người truy cập (lần truy cập tiếp theo mất ~30 giây để khởi động lại). Bạn có thể tạo tài khoản miễn phí tại **UptimeRobot.com** hoặc **Cron-job.org**, đặt lịch ping vào `https://<ten-app>.onrender.com/api/auth/status` mỗi **10 phút** để giữ web luôn thức 24/7 hoàn toàn miễn phí!

---

## Phương Án 3: Đóng Gói Thành Phần Mềm Desktop `.exe` (Chi Phí Server = 0đ)

Khi bán cho các nhà máy/doanh nghiệp tại Việt Nam, nhiều khách hàng thích một **phần mềm chạy trực tiếp trên máy tính Windows của kế toán/HSE** (vừa bảo mật hóa đơn nội bộ 100%, vừa không tốn một đồng tiền thuê server đám mây nào cho bạn).

Dự án đã tích hợp sẵn bộ đóng gói tự động tại [`scripts/desktop_launcher.py`](file:///d:/Workspace/EcoStream/scripts/desktop_launcher.py) và [`scripts/build_desktop_exe.bat`](file:///d:/Workspace/EcoStream/scripts/build_desktop_exe.bat):

### Cách xuất file `.exe`:
1. Mở Terminal / Command Prompt tại thư mục gốc dự án và chạy:
   ```powershell
   .\scripts\build_desktop_exe.bat
   ```
2. Sau khi chạy xong, toàn bộ phần mềm sẽ nằm trong thư mục `dist/EcoStream_Carbon_AI/`.
3. Bạn chỉ cần nén thư mục `EcoStream_Carbon_AI.zip` gửi cho doanh nghiệp. Khi khách hàng bấm đúp vào `EcoStream_Carbon_AI.exe`, phần mềm sẽ tự động bật máy chủ ngầm và mở ngay giao diện Dashboard trên trình duyệt của họ!

---

## 🔐 Hướng Dẫn Quản Lý Đa Thuê Bao (Multi-Tenant) & Kích Hoạt License Pro

Hệ thống đã được tích hợp sẵn cơ chế phân quyền doanh nghiệp và phân tầng gói cước ngay trên giao diện chính (`/`):

### 1. Đăng nhập Doanh nghiệp & Cô lập dữ liệu (`org_id`)
- Nhấn vào nút **`🔒 Khách (Free) | FREE PREVIEW`** trên thanh tiêu đề góc phải.
- Nhập **Email Cán bộ** và **Mã Tổ Chức (`Org ID`)** (ví dụ: `ecogarment-vn`, `vinatex-hn`).
- Mọi phiên tính toán (`run_id`) sẽ được gắn nhãn `org_id` riêng biệt (`runs/<run_id>/tenant_meta.json`), và các nút tải báo cáo HTML/PDF/Word/Excel sẽ tải chính xác theo `run_id` của phiên đó (không bị chồng chéo khi nhiều công ty cùng sử dụng).

### 2. Cơ chế Free Preview (Watermark) vs. Gói Pro / Enterprise
- **Gói Free Preview (Mặc định khi chưa nhập License)**:
  - Cho phép chạy tính toán đầy đủ các chỉ số KPI và xem bảng chi tiết bóc tách.
  - Báo cáo **HTML** và **PDF** khi mở sẽ có đóng dấu chìm **`BẢN XEM TRƯỚC DÙNG THỬ (FREE PREVIEW)`**.
  - Hai nút tải **Word Mẫu 02 NĐ 06/2022 (`🔒 PRO`)** và **Hồ Sơ Excel (`🔒 PRO`)** sẽ bị khóa.
- **Kích hoạt Gói Pro / Enterprise**:
  - Mở hộp thoại Tài khoản Doanh nghiệp và nhập một trong các mã License mặc định:
    - `ECO-PRO-2026`
    - `ECO-ENTERPRISE-2026`
    - `USTH-INNO-2026`
    *(Hoặc cấu hình danh sách mã riêng của bạn qua biến môi trường `ECOSTREAM_PRO_KEYS=KEY1,KEY2` trên server).*
  - Ngay sau khi kích hoạt, huy hiệu chuyển thành **`💎 PRO VERIFIED`**, dấu Watermark trên HTML/PDF được gỡ bỏ hoàn toàn và mở khóa tải trực tiếp file **Word Mẫu 02** & **Hồ sơ kiểm toán Excel**.


