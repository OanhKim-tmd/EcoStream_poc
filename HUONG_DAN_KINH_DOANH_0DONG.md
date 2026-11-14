# HƯỚNG DẪN KINH DOANH & PHÁT HÀNH ECOSTREAM CHI PHÍ 0 ĐỒNG

Tài liệu này cung cấp toàn bộ quy trình vận hành thương mại hóa **EcoStream AI Carbon Accounting** dành cho giai đoạn Startup / MVP với **chi phí bản quyền và hạ tầng là 0 VNĐ**.

---

## 1. CƠ CHẾ BẢN QUYỀN (LICENSING) — 0 ĐỒNG SERVER

Hệ thống sử dụng **Chữ ký số bất đối xứng Ed25519 (Asymmetric Digital Signature)**:
- **Private Key**: Lưu bí mật trên máy tính của bạn tại [scripts/vendor_ed25519_private.key](file:///Users/vanpham/Documents/Workspace/EcoStream/scripts/vendor_ed25519_private.key). File này đã được thêm vào `.gitignore`, **tuyệt đối không gửi cho khách hàng hay commit lên Git public**.
- **Public Key**: Đã nhúng sẵn vào mã nguồn EcoStream trong [licensing.py](file:///Users/vanpham/Documents/Workspace/EcoStream/ecostream/privacy/licensing.py). Khách hàng dù dịch ngược code cũng **không thể tự làm giả key**.

### Cách tạo mã License Key khi có khách mua:
Mở terminal và chạy lệnh:
```bash
# Ví dụ 1: Cấp key 1 năm cho Công ty Dệt May EcoGarment
python scripts/generate_license_key.py --org "ecogarment-vn" --email "ceo@ecogarment.vn" --expires 2027-12-31 --plan PRO

# Ví dụ 2: Cấp key gói Enterprise vĩnh viễn hoặc dài hạn
python scripts/generate_license_key.py --org "vinamilk" --email "esg@vinamilk.com.vn" --expires 2030-12-31 --plan ENTERPRISE
```

Hệ thống sẽ in ra chuỗi mã dạng:
`ECO2.eyJlbWFpbCI6...W_iqOVzXObdt...`

Bạn chỉ cần copy chuỗi này gửi qua Email / Zalo cho khách hàng. Khách dán vào EcoStream là mở khóa toàn bộ tính năng:
- Bỏ dấu Watermark trên báo cáo.
- Mở khóa xuất file Word Mẫu 02 Nghị định 06/2022/NĐ-CP (`.docx`).
- Mở khóa xuất Hồ sơ kiểm toán dữ liệu phát thải (`.xlsx`).

---

## 2. CƠ CHẾ AI / LLM — 0 ĐỒNG CHI PHÍ TOKEN

1. **Bộ tính toán phát thải (Scope 1, 2, 3):**
   Chạy 100% bằng thuật toán toán học cục bộ theo hệ số phát thải Việt Nam & IPCC. **Không tốn 1 đồng chi phí AI nào.**

2. **Bóc tách hóa đơn & Gợi ý giảm phát thải:**
   EcoStream đã tích hợp sẵn cơ chế **BYOK (Bring Your Own Key)** với **Google Gemini API Free**:
   - Google AI Studio cấp miễn phí **1.500 lượt gọi/ngày** với Gemini 1.5 / 2.0 Flash.
   - **Hướng dẫn cho khách:** Trong giao diện EcoStream, bấm vào icon Tài khoản góc phải -> chọn *Cấu hình AI* -> Bấm *"🔑 Lấy Gemini Key Free"* (đăng nhập Gmail là có ngay key trong 30 giây) -> Dán vào app.
   - Mọi dữ liệu hóa đơn đều đi qua bộ lọc che PII ([pii_masker.py](file:///Users/vanpham/Documents/Workspace/EcoStream/ecostream/privacy/pii_masker.py)) trước khi gửi, đảm bảo không rò rỉ thông tin mật của doanh nghiệp.

---

## 3. CÁCH ĐÓNG GÓI BỘ CÀI ĐẶT CHUYÊN NGHIỆP

### A. Đóng gói cho macOS (`.dmg`):
Chạy script tự động:
```bash
python scripts/build_desktop_app.py
```
File installer sẽ nằm tại: `dist/EcoStream-Installer.dmg`. Khách tải về chỉ cần kéo thả `EcoStream.app` vào thư mục `Applications`.

### B. Đóng gói cho Windows (`.exe` Setup):
1. **Bước 1:** Chạy PyInstaller để build thư mục app:
   ```cmd
   build_windows_exe.bat
   ```
2. **Bước 2 (Tạo file Setup chuyên nghiệp):**
   - Tải phần mềm miễn phí [Inno Setup](https://jrsoftware.org/isdl.php).
   - Mở file [scripts/installer_windows.iss](file:///Users/vanpham/Documents/Workspace/EcoStream/scripts/installer_windows.iss) bằng Inno Setup và bấm nút **Compile** (hoặc phím tắt `Ctrl + F9`).
   - Kết quả xuất ra file: `dist/EcoStream_Windows_Setup_v1.0.exe`.

---

## 4. QUY TRÌNH NÉ CẢNH BÁO VIRUS (FALSE POSITIVE) MIỄN PHÍ

Khi chưa có chứng chỉ số thương mại (Code Signing Certificate), bạn làm theo 3 bước sau:

### Trên Windows:
1. **Nộp file lên Microsoft Security Intelligence (Miễn phí 100%):**
   - Truy cập: [https://www.microsoft.com/en-us/wdsi/filesubmission](https://www.microsoft.com/en-us/wdsi/filesubmission)
   - Chọn mục **Software Developer** -> Tải file `EcoStream_Windows_Setup_v1.0.exe` lên.
   - Chọn lý do: *"Incorrectly detected as malware / False Positive"*.
   - Microsoft sẽ quét và đưa app của bạn vào whitelist cập nhật định nghĩa virus của Windows Defender trong vòng 24 - 48 giờ.
2. **Hướng dẫn người dùng khi gặp SmartScreen (Màn hình xanh):**
   - Tạo 1 ảnh chụp màn hình kèm hướng dẫn trên Landing page:
     > *"Khi xuất hiện thông báo 'Windows protected your PC' -> Bấm **More info** -> Chọn **Run anyway**"*.

### Trên macOS:
- Khi người dùng mở app lần đầu nếu gặp thông báo Gatekeeper:
  > *"Click chuột phải vào icon EcoStream trong Applications -> Chọn **Open** -> Bấm **Open** lần 2"*. (Chỉ cần làm 1 lần duy nhất).

---

## 5. THIẾT LẬP THANH TOÁN VIETQR TỰ ĐỘNG (0 ĐỒNG PHÍ DUY TRÌ)

Để bán tự động 24/7 mà không cần bạn phải trực ngồi cấp key:
1. Đăng ký tài khoản miễn phí tại **PayOS** ([payos.vn](https://payos.vn)) hoặc **SePay** ([sepay.vn](https://sepay.vn)).
2. Liên kết tài khoản ngân hàng cá nhân của bạn (MB, VCB, ACB, TPBank...).
3. Chạy script webhook tự động cấp key:
   ```bash
   uvicorn scripts.payment_webhook_server:app --port 8080
   ```
4. Khi khách quét mã VietQR thanh toán 990.000 VNĐ (gói Pro):
   - PayOS gửi webhook về server -> Server tự động gọi `generate_ed25519_license()` -> Gửi email mã key kèm link tải cho khách ngay lập tức!

