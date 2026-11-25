# EcoStream

**EcoStream** là ứng dụng web thử nghiệm hỗ trợ thu thập chứng từ, điền biểu khảo sát kiểm kê khí nhà kính cấp cơ sở, tính toán một phần Scope 1/2 và xuất bản nháp đối soát. Dự án được xây dựng dựa trên các biểu mẫu và tài liệu tham khảo về kiểm kê KNK tại Việt Nam trong `data/test_documents/`.

> Đây là công cụ hỗ trợ xử lý dữ liệu, không thay thế chuyên gia kiểm kê, quy trình MRV, thẩm định độc lập hay tư vấn pháp lý. Kết quả phải được cơ sở kiểm tra với chứng từ gốc, hệ số và phương pháp áp dụng cho kỳ báo cáo trước khi sử dụng chính thức.

## Phạm vi hoạt động hiện tại

Luồng khảo sát chính:

1. Tải chứng từ lên giao diện web và khai báo doanh nghiệp, cơ sở, năm báo cáo.
2. EcoStream nhận dạng một số dòng dữ liệu hoạt động từ định dạng được hỗ trợ, tạo bản sao biểu khảo sát và ghi lại tệp đã/chưa dùng cùng cảnh báo.
3. Người dùng rà soát, bổ sung hoặc sửa biểu khảo sát trong giao diện/tệp Excel.
4. Chạy tính toán từ biểu đã rà soát và tải xuống workbook kiểm kê cùng báo cáo Word dự thảo.

Phạm vi tính hiện thực hiện là **một phần các nguồn Scope 1 và Scope 2 được ánh xạ giữa biểu khảo sát và workbook kiểm kê**. Không coi các ô không có dữ liệu là số 0; ứng dụng không tự suy diễn lượng tiêu thụ, không nội suy tháng thiếu và không tự tính mức giảm nhẹ/hạn ngạch khi thiếu dữ liệu, phương pháp và bằng chứng cần thiết.

Toàn bộ tính năng là **miễn phí và mở hoàn toàn**: không có tài khoản, gói Pro, mã bản quyền hay watermark. Mọi tệp kết quả đều tải được ngay sau khi tính.

### Nhiên liệu được tính vào tổng phát thải

Chỉ nhiên liệu có **hệ số phát thải riêng** trong EcoStream mới được cộng vào tổng: than (antraxit, bitum, sub-bitum, than trộn), dầu DO, dầu FO, xăng, khí tự nhiên, LPG và điện lưới.

Các nhiên liệu sau vẫn được ghi vào biểu khảo sát nhưng **chưa được cộng vào tổng** và được liệt kê "CHƯA TÍNH" trong cảnh báo và báo cáo:

- Sinh khối (gỗ, than củi, bã mía, trấu, rơm rạ, viên nén, biogas, nhiên liệu sinh học lỏng). Theo IPCC 2006, CO₂ từ sinh khối được báo cáo riêng, còn CH₄/N₂O cần hệ số riêng.
- Chất thải dùng làm nhiên liệu, than bùn, LNG, dầu hỏa và các sản phẩm dầu mỏ khác. EcoStream chưa có hệ số riêng cho các loại này.

Phiên bản trước mượn hệ số than, diesel hoặc LPG cho các nhiên liệu này, khiến kết quả sai. Cách làm đó đã bị bỏ: chuyên gia cần bổ sung hệ số trước khi các nguồn này được tính.

Cột mã vật tư, nhiệt trị, thiết bị và nhà cung cấp trong sheet 1.1 chỉ được điền từ chứng từ hoặc do người dùng nhập; ứng dụng không tự điền giá trị mẫu.

### Cách EcoStream đọc chứng từ

EcoStream chỉ đọc chứng từ **có lớp chữ**: Excel, Word, CSV, và **PDF có chữ** (ví dụ hóa đơn điện tử, bản xuất từ phần mềm kế toán). Mọi xử lý chạy trên máy:

- **Microsoft MarkItDown** và **pypdf** chuyển Excel, Word, PDF thành văn bản có cấu trúc.
- **Bộ nhận dạng theo quy tắc** xác định loại nhiên liệu, kỳ hóa đơn, lượng, đơn vị và loại bỏ hóa đơn trùng.

EcoStream **không dùng OCR**. Ảnh (`.png`, `.jpg`…) bị từ chối ngay khi tải lên. PDF dạng scan (không có lớp chữ) vẫn tải lên được, nhưng ứng dụng sẽ cảnh báo "PDF không có lớp chữ", và người dùng nhập số liệu đó thủ công ở bước rà soát. Hóa đơn điện tử tại Việt Nam là PDF có chữ, nên trường hợp phổ biến không bị ảnh hưởng.

Phép tính phát thải (lượng × hệ số) là **tất định** bằng Python, không dùng mô hình ngôn ngữ, nên cùng dữ liệu luôn cho cùng kết quả và kiểm tra lại được từng dòng. Ứng dụng **không gửi chứng từ tới dịch vụ AI bên ngoài** (Gemini, OpenAI…) và không cần khóa API.

### Đã gỡ: pipeline multi-agent cũ

Pipeline multi-agent cũ (`ecostream/agents/`, `ecostream/extraction/`, `orchestrator/pipeline.py`, `cli.py`, các endpoint `/api/demo`, `/api/upload`, `/api/export/*`, `/api/report/*`) đã được xóa khỏi mã nguồn. Sản phẩm hiện tại chỉ có **luồng khảo sát** mô tả trong tài liệu này. Trang `/monitor` vẫn đọc các run trong `runs/` qua `/api/orchestrator/runs`.

## Cài đặt cho người dùng (ứng dụng desktop)

Người dùng không cần cài Python. Tải bộ cài tại trang Releases của dự án:

**https://github.com/OanhKim-tmd/EcoStream_poc/releases/latest**

| Hệ điều hành | Tệp | Cách cài |
| --- | --- | --- |
| Windows 10/11 | `EcoStream-Windows-Setup.exe` | Chạy bộ cài. Nếu hiện "Windows protected your PC": bấm **More info → Run anyway**. |
| macOS | `EcoStream-Installer.dmg` | Mở tệp, kéo EcoStream vào Applications. Lần đầu mở: chuột phải → **Open** → **Open**. |

Ứng dụng chưa được ký số, nên Windows và macOS sẽ cảnh báo ở lần chạy đầu. Khi mở, EcoStream hiện trong **cửa sổ ứng dụng riêng** (thư viện `pywebview`: WebView2 có sẵn trên Windows 10/11, WKWebView có sẵn trên macOS), không mở Chrome, Edge hay Safari. Bên trong, ứng dụng chạy một máy chủ cục bộ tại `127.0.0.1` mà người dùng không nhìn thấy. Đóng cửa sổ là thoát hẳn ứng dụng. Kết quả được lưu trong `%LOCALAPPDATA%\EcoStream\runs` (Windows) hoặc `~/Library/Application Support/EcoStream/runs` (macOS).

Bản desktop có đủ chức năng như bản chạy từ mã nguồn: đọc Excel, Word, CSV và PDF có chữ (không đọc ảnh hoặc PDF scan, xem mục "Cách EcoStream đọc chứng từ").

### Phát hành phiên bản mới (dành cho nhóm phát triển)

Workflow `.github/workflows/build-desktop.yml` tự build và tự kiểm tra (chạy thử server và giao diện) trên máy Windows và macOS của GitHub. Để đăng bản mới lên trang Releases:

```bash
git tag v0.3.0
git push origin v0.3.0
```

Sau khoảng 10–15 phút, bộ cài xuất hiện tại link Releases ở trên. Repository cần ở chế độ **public** để người ngoài tải được. Muốn build thủ công trên máy, hãy dùng môi trường ảo sạch. Nếu build trong môi trường chung (như conda base), app có thể bị gom thêm các thư viện AI không dùng tới:

```bash
python -m venv .venv-build
.venv-build/bin/pip install -r requirements-desktop.txt
.venv-build/bin/python scripts/build_desktop_app.py
dist/EcoStream/EcoStream --headless-check   # in ra "[headless-check] OK" nếu app chạy được
```

Kết quả nằm trong `dist/`. Trên Windows, thay `.venv-build/bin/` bằng `.venv-build\Scripts\`.

## Cài đặt và chạy từ mã nguồn

Yêu cầu: Python 3.10 trở lên. Từ thư mục gốc dự án:

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m ecostream.app
```

Ứng dụng in địa chỉ máy chủ khi khởi động (thường là `http://127.0.0.1:8000`). Mở địa chỉ đó trong trình duyệt. Dừng máy chủ bằng `Ctrl+C`.

- `/` — giao diện khảo sát và kết quả.
- `/docs` — tài liệu API của luồng khảo sát.

Trang monitor kỹ thuật `/monitor` vẫn có trong mã nguồn để debug pipeline cũ, nhưng không nằm trong luồng người dùng cuối.

### Chạy không cần Internet

Sau khi cài đặt xong, ứng dụng **chạy hoàn toàn offline**:

- Giao diện dùng stylesheet và phông chữ lưu sẵn trong `ecostream/app/static/vendor/`, không tải gì từ CDN.
- Đọc chứng từ, điền biểu, tính toán và xuất Excel/Word đều chạy trên máy.

Chỉ cần mạng một lần khi `pip install`. Bản desktop không cần mạng chút nào.

Mặc định API chạy không cần khóa trong môi trường phát triển cục bộ. Có thể đặt `ECOSTREAM_API_KEY` để yêu cầu khóa cho các endpoint được bảo vệ; gửi khóa qua header `X-API-Key`. Không mở máy chủ ra Internet nếu chưa thiết lập xác thực, phân quyền, HTTPS và chính sách lưu trữ phù hợp.

## Chứng từ đầu vào

Endpoint khảo sát hiện nhận tối đa 100 tệp (có thể đổi bằng `ECOSTREAM_MAX_SURVEY_FILES`), mỗi tệp tối đa 10 MB, với đuôi `.xlsx`, `.csv`, `.pdf`, `.docx`. Ảnh bị từ chối; PDF scan được nhận nhưng chỉ sinh cảnh báo nhập thủ công. Luôn xem trạng thái và cảnh báo trong giao diện.

Việc tự điền phụ thuộc định dạng và cách trình bày chứng từ. Một số dòng nhiên liệu và điện có tháng, lượng, đơn vị rõ ràng có thể được nhận dạng; chứng từ bố cục khác, thiếu dữ liệu hoặc không được hỗ trợ cần nhập/rà soát thủ công. Không mặc định dữ liệu trong mọi tệp sẽ được trích xuất chính xác.

Đầu ra của luồng khảo sát được lưu dưới `runs/<run_id>/deliverables/`:

- `Bang_khao_sat_da_dien.xlsx` — bản khảo sát để rà soát.
- `GHGs_inventory_da_tinh.xlsx` — workbook kiểm kê đã điền các trường được hỗ trợ.
- `Bao_cao_kiem_ke_KNK.docx` — báo cáo Word dự thảo.

Thư mục `runs/` là dữ liệu sinh ra khi chạy, không phải mã nguồn. Giữ lại hoặc sao lưu các phiên cần thiết; không chia sẻ chứng từ doanh nghiệp nếu chưa được phép.

## Chạy thử

Có thể dùng bộ dữ liệu giả lập đã có:

```bash
python -m ecostream.app
```

Mở giao diện, điền thông tin cơ sở rồi tải các tệp trong `data/demo_full_2026/` theo hướng dẫn tại `data/demo_full_2026/README.txt`. Dữ liệu này chỉ phục vụ thử nghiệm, không phải chứng từ thật hay kết quả đã thẩm định. Để tạo lại một số bộ demo, xem các script `scripts/generate_*.py` tương ứng.

## Kiểm thử

```bash
python -m unittest discover -s tests
```

### Sửa giao diện

Giao diện dùng Tailwind CSS build sẵn (`ecostream/app/static/vendor/app.css`) và phông chữ trong `vendor/fonts/`. Nếu thêm class Tailwind mới vào `index.html`, `monitor.html` hoặc `monitor.js`, hãy build lại. Bước này cần Node.js và mạng một lần:

```bash
bash scripts/build_offline_assets.sh
```

## Tài liệu nguồn trong `data/test_documents/`

Thư mục này lưu tài liệu tham khảo và mẫu nghiệp vụ để phát triển/đối chiếu, không phải thư mục đầu vào bắt buộc khi chạy ứng dụng:

| Tệp | Nội dung nhận diện từ tài liệu |
| --- | --- |
| `06.01.2025.-Bang-khao-sat-SLHD-cap-co-so-VN.xlsx` | Biểu khảo sát số liệu hoạt động cấp cơ sở; ứng dụng dùng tệp này làm mẫu khảo sát. |
| `17-btnmt.pdf` | Thông tư 17/2022/TT-BTNMT; tài liệu về kỹ thuật đo đạc, báo cáo, thẩm định giảm nhẹ phát thải và kiểm kê KNK trong lĩnh vực quản lý chất thải. |
| `20.05.25.-IE.-QDPL-Viet-Nam-ve-KK-KNK-Ms.-Huyen.pdf` | Tài liệu trình bày các quy định pháp luật Việt Nam về kiểm kê KNK, do Viện Năng lượng trình bày (05/2025). |
| `20.5.2025.-Dao-tao-KK-KNK-co-so-thuc-hanh.pdf` | Tài liệu hướng dẫn thực hành kiểm kê KNK cấp cơ sở cho nhà máy nhiệt điện than (05/2025). |
| `20.5.2025.-Tong-quan-ppl-theo-IPCC.pdf` | Tài liệu tổng quan phương pháp luận kiểm kê KNK theo hướng dẫn quốc tế và quy định Việt Nam (05/2025). |
| `2.-ND06._GHGs-Report-NS2PC_Final_VN (1).docx` | Báo cáo kiểm kê KNK của một cơ sở/doanh nghiệp; tài liệu tham khảo cấu trúc và nội dung báo cáo. |
| `2. Pham_vi_cong_viec_Bao_cao_ket_qua_giam_nhe_KNK_NMND.docx` | Tài liệu phạm vi công việc báo cáo kết quả giảm nhẹ KNK cho nhà máy nhiệt điện. |
| `Bao_cao_cụ_thể_theo_mau_ND06.docx` | Báo cáo mẫu/tham khảo theo cấu trúc Nghị định 06. |
| `_GHGs-inventory.xlsx` | Workbook kiểm kê KNK mẫu, dùng tham khảo cấu trúc bảng tính. |
| `USTH_Inn 2026_EcoStream - Dịch vụ kiểm kê phân tich phát thải carbon được hỗ trợ bởi nền tảng AI (4).docx` | Tài liệu giới thiệu/đề xuất EcoStream; không phải đặc tả xác nhận mọi tính năng đã triển khai. |

Danh mục trên chỉ mô tả nội dung nhận diện được từ tên và tài liệu; cần đọc bản gốc để xác minh điều khoản, hiệu lực, biểu mẫu và phương pháp. Phần mềm không tự bảo đảm tuân thủ chỉ vì tham chiếu các tài liệu này.

## Cấu trúc chính

```text
ecostream/                 Ứng dụng Python: web, khảo sát, tính toán, ingestion, báo cáo
  app/                     FastAPI và giao diện tĩnh (static/vendor/: CSS và phông chữ offline)
  ingestion/               Đọc/chuyển đổi chứng từ (MarkItDown, pypdf) và biểu mẫu khảo sát
  orchestrator/            survey_pipeline.py: luồng khảo sát; state.py: workspace theo run
  reporting/               Tạo workbook/báo cáo
  factors/                  Cơ sở hệ số trong ứng dụng
data/
  test_documents/          Biểu mẫu và tài liệu nguồn tham khảo
  samples/, demo_full_2026/ Dữ liệu mẫu và dữ liệu giả lập
runs/                      Kết quả phát sinh (được bỏ qua khỏi Git)
tests/                     Kiểm thử tự động
scripts/                    Tiện ích tạo dữ liệu và đóng gói
```

## Ghi chú về phương pháp và pháp lý

Tài liệu nguồn trong repository gồm Thông tư 17/2022/TT-BTNMT và tài liệu đào tạo/tổng quan được lưu trong `data/test_documents/`. Đây là nguồn tham khảo, không phải tư vấn pháp lý hoặc khẳng định về hiệu lực hiện hành. Trước khi lập báo cáo chính thức, cần đối chiếu văn bản pháp luật mới nhất, biểu mẫu có thẩm quyền, ranh giới kiểm kê, hệ số phát thải đúng kỳ và phương pháp áp dụng cho cơ sở.

Các tổng hợp do phần mềm tạo là kết quả xử lý theo dữ liệu đầu vào và logic đang triển khai; không mặc định tương đương kết quả trong workbook tham khảo, không được xem là báo cáo đã thẩm định và không tự động xác nhận điều kiện giảm nhẹ phát thải/hạn ngạch.

## Đóng góp

Chạy test trước khi gửi thay đổi. Không đưa chứng từ, thông tin cá nhân, khóa API, khóa ký hoặc dữ liệu nội bộ của doanh nghiệp vào Git. Giấy phép dự án xem tại [LICENSE](LICENSE).
