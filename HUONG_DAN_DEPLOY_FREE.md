# Triển khai EcoStream

Tài liệu này ghi chú triển khai Docker cho môi trường thử nghiệm. Không có nền tảng nào được bảo đảm miễn phí, luôn sẵn sàng hoặc phù hợp để lưu chứng từ nhạy cảm. Hãy kiểm tra giá, điều khoản, giới hạn tài nguyên và vùng lưu trữ hiện hành của nhà cung cấp.

## Docker

Trong repository có `Dockerfile` và `docker-compose.yml`. Build và chạy:

```bash
docker compose build
docker compose up
```

Compose ánh xạ cổng máy chủ 8000 vào cổng 8000 trong container và mount `runs/`, `data/samples/` từ máy chủ. Dừng bằng `Ctrl+C`; để chạy nền có thể dùng `docker compose up -d` và dừng bằng `docker compose down`.

Trước khi triển khai:

- **Hai biến bắt buộc.** Server từ chối khởi động trên địa chỉ mạng nếu thiếu một trong hai:
  - `ECOSTREAM_API_KEY`: tối thiểu 16 ký tự. Tạo bằng `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
  - `ECOSTREAM_ENCRYPTION_KEY`: khóa mã hóa file gốc. Tạo bằng `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
  - Đặt bằng secret manager hoặc biến môi trường bảo mật, hoặc tệp `.env` không commit vào Git. Không ghi khóa thật vào compose file. Đổi `ECOSTREAM_ENCRYPTION_KEY` sau này sẽ làm các file đã lưu không còn giải mã được, nên hãy lưu khóa ở nơi an toàn.
- Container chạy bằng user `ecostream` (uid 1000). Thư mục `runs/` trên máy chủ phải ghi được bởi uid 1000 (`sudo chown -R 1000:1000 runs`).
- Đặt reverse proxy/HTTPS, xác thực người dùng và kiểm soát truy cập phù hợp. API key chia sẻ không thay thế phân quyền đa người dùng.
- Bảo vệ ổ lưu trữ `runs/`; dữ liệu tải lên có thể chứa thông tin doanh nghiệp/cá nhân.
- Đánh giá backup, retention, xóa dữ liệu, giám sát lỗi và cập nhật dependency.
- Chạy test và thử bằng dữ liệu không nhạy cảm trước khi mở dịch vụ.

Các cấu hình `render.yaml` và `railway.json` là cấu hình triển khai tùy chọn có trong repository; việc tồn tại của chúng không khẳng định dịch vụ đang được duy trì hay có chi phí bằng 0. Không triển khai trực tiếp lên Internet nếu chưa hoàn tất các biện pháp bảo mật ở trên.

## Ứng dụng desktop

Cách phân phối khuyến nghị cho người dùng cuối là **ứng dụng desktop**: không cần máy chủ, không tốn phí và chứng từ không rời khỏi máy người dùng.

- Đóng gói bằng PyInstaller (`scripts/build_desktop_app.py`) và launcher `scripts/desktop_launcher.py`. Bộ cài Windows được tạo bằng Inno Setup (`scripts/installer_windows.iss`).
- GitHub Actions (`.github/workflows/build-desktop.yml`) build trên Windows và macOS, chạy kiểm tra `--headless-check`, rồi khi có tag `v*` thì đăng bộ cài lên GitHub Releases.
- Link gửi người dùng: `https://github.com/OanhKim-tmd/EcoStream_poc/releases/latest`. Hướng dẫn cài đặt và giới hạn của bản desktop nằm trong [README.md](README.md).

Bản Tauri (`src-tauri/`) cũ đã bị gỡ ở phiên bản 0.3.0, vì nó chỉ đóng gói giao diện tĩnh mà không có máy chủ Python nên không xử lý được chứng từ.

Ứng dụng chưa ký số (code signing), nên Windows SmartScreen và macOS Gatekeeper sẽ cảnh báo ở lần chạy đầu. Muốn bỏ cảnh báo cần mua chứng chỉ ký số và Apple Developer ID.
