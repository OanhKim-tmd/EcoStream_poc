# Changelog — EcoStream

Lịch sử thay đổi tính năng của EcoStream. Các mục cũ phản ánh trạng thái tại thời điểm ghi nhận, không phải cam kết phạm vi hiện hành. Xem [README.md](README.md) để biết luồng đang được ưu tiên.

---

## [0.3.0] - 2026-11-25 — Chuẩn bị dự thi Cảm hứng Sáng tạo USTH

### Sửa phương pháp tính
- Nhiên liệu không có hệ số phát thải riêng (sinh khối, biogas, nhiên liệu sinh học lỏng, chất thải, than bùn, LNG, dầu hỏa, sản phẩm dầu mỏ khác) **không còn mượn hệ số** than/diesel/LPG/khí tự nhiên. Các dòng này được giữ trong biểu khảo sát, không cộng vào tổng, và được liệt kê "CHƯA TÍNH" trong cảnh báo và báo cáo.
- Biểu khảo sát không còn tự điền mã vật tư, nhiệt trị, thiết bị và nhà cung cấp bằng giá trị mẫu (ví dụ "Petrolimex", "TKV").
- Ghi rõ nguồn hệ số điện lưới 0,7221 tCO₂/MWh và yêu cầu đối chiếu công bố mới nhất.

### Gỡ bản quyền / gói Pro
- Xóa khóa PRO, watermark "FREE PREVIEW", mã dùng thử công khai và secret ký HMAC nằm trong mã nguồn.
- Xóa `ecostream/privacy/licensing.py`, `scripts/generate_license_key.py`, `scripts/payment_webhook_server.py`, endpoint `/api/auth/login`, `/api/license/verify` và biến `ECOSTREAM_PRO_KEYS`.

### AI và đọc chứng từ
- Gỡ màn hình nhập khóa API Gemini/OpenAI và endpoint `/api/settings/ai`. Luồng khảo sát không gọi dịch vụ AI bên ngoài.
- **Gỡ toàn bộ OCR** (EasyOCR, pytesseract, pdf2image, Pillow; Tesseract/Poppler trong Dockerfile). Chỉ đọc chứng từ có lớp chữ: Excel, Word, CSV, PDF có chữ. Ảnh bị từ chối khi tải lên; PDF scan sinh cảnh báo "PDF không có lớp chữ" để nhập thủ công. Xóa ảnh mẫu `data/hóa đơn xăng dầu.png`.

### Một luồng duy nhất
- Giao diện chỉ còn luồng khảo sát với 3 tệp kết quả (biểu khảo sát, workbook kiểm kê, báo cáo Word). Bỏ các nút HTML/PDF của pipeline cũ.
- Ẩn các endpoint pipeline cũ (`/api/demo`, `/api/upload`, `/api/report/*`, `/api/export/*`) khỏi `/docs`. Mã vẫn giữ cho CLI và test.
- Xóa `ecostream/app/static/workflow.html` và `ecostream_workflow_visualizer.html` (không còn route nào phục vụ).

### Giao diện mới (bố cục dashboard, tone xanh lá)
- Khung ứng dụng bo góc trên nền xanh đậm; thanh điều hướng bên trái chứa 4 bước, mục đang chọn nối liền vào vùng nội dung.
- Thanh tiêu đề hiển thị bước hiện tại và tên cơ sở; thẻ chào có minh họa, lời hướng dẫn đổi theo từng bước.
- Cột phải (màn hình rộng): timeline tiến trình 4 bước và các lưu ý quan trọng (PDF có chữ, nhiên liệu CHƯA TÍNH, bản dự thảo).
- Bước kết quả có biểu đồ cột phát thải theo tháng (Scope 1/2 chồng) và biểu đồ vòng tỷ trọng Scope 1/2, vẽ bằng SVG/CSS nên vẫn chạy offline.

### Chạy không cần Internet
- Thay Tailwind Play CDN và Google Fonts bằng stylesheet build sẵn cùng phông Inter/JetBrains Mono lưu trong `ecostream/app/static/vendor/`.

### Ứng dụng desktop và link tải
- Workflow `build-desktop.yml` build bộ cài Windows (`EcoStream-Windows-Setup.exe`) và macOS (`EcoStream-Installer.dmg`), tự kiểm tra bằng `--headless-check`, và đăng lên GitHub Releases khi push tag `v*`.
- Thêm chế độ `--headless-check` vào `scripts/desktop_launcher.py`. Trên Windows/macOS, chế độ này báo lỗi nếu bản build thiếu `pywebview`.
- App desktop mở trong **cửa sổ ứng dụng riêng** bằng `pywebview` (thêm `requirements-desktop.txt`), không còn mở trình duyệt. Chỉ khi máy thiếu WebView2 mới quay về mở bằng trình duyệt.
- Sửa `installer_windows.iss` (ký tự lỗi ở dòng đầu, tên tệp và phiên bản).
- Gỡ `src-tauri/` và `build-tauri.yml`: bản Tauri không có máy chủ Python nên không chạy được.

### Khác
- Bỏ đường dẫn máy cá nhân hard-code trong `markitdown_normalizer.py`.
- Khôi phục `data/samples/sample_evn_bill.pdf` mà test cần.

### Nhật ký xử lý
- Bỏ link `/monitor` khỏi giao diện người dùng cuối; README và hướng dẫn ghi rõ đây là công cụ kỹ thuật cho pipeline cũ.
- Bảo vệ trang `/monitor`, script `/monitor.js` và API liệt kê phiên `/api/orchestrator/runs` bằng `ECOSTREAM_API_KEY` nếu cấu hình.

## Ghi chú hiện trạng — 2026-11-25

- Tài liệu hướng dẫn đã được đồng bộ theo luồng khảo sát hiện hành, đầu ra và giới hạn thực tế; các tuyên bố cũ về tuân thủ/đầu ra không áp dụng mặc nhiên.
- Bỏ metadata hệ điều hành và các bản cache ingestion được commit nhầm; cache phát sinh được lưu trong `.cache/ecostream/ingestion/`.

## [0.2.0] - 2026-09-29

### 🚀 Major Architectural Refactoring: AI Multi-Agent, Blackboard Orchestrator & Live Monitor

#### Added
- **Multi-Agent Blackboard Architecture (`ecostream/orchestrator/`)**:
  - Isolated run workspaces under `runs/<run_id>/` managing `state.json`, `index.json`, intermediate extractions (`intermediate/*.json`), dual logs, and deliverables.
  - Lifecycle state machine supporting 5 phases: `INGESTION` $\to$ `DISCOVERY` $\to$ `EXTRACTION` $\to$ `MATH_AND_MITIGATION` $\to$ `SYNTHESIS` $\to$ `COMPLETED`.
- **Microsoft MarkItDown Universal Ingestion & OCR (`ecostream/ingestion/`)**:
  - `markitdown_loader.py` & `markitdown_normalizer.py`: Seamlessly converts multi-tab Excel (`.xlsx`), PDF, Word (`.docx`), PowerPoint, and CSV files into modular Markdown inputs (`input_<SheetName>.md`).
  - Integrated `pytesseract` and `pdf2image` with dual language support (`vie+eng`) for local OCR processing of scanned bills.
  - `cache.py`: SHA-256 fingerprint caching avoiding re-processing unmodified documents.
- **Specialized Domain Subagents (`ecostream/agents/` & `.claude/agents/`)**:
  - `ag-discovery`: Schema discovery, sheet cataloging, and task routing in `index.json`.
  - `ag-scope1-fuel`: Stationary & mobile fuel combustion extraction (diesel, gasoline, coal, LPG packaging conversions).
  - `ag-scope2-power`: EVN utility grid power invoice extraction with seasonal linear interpolation for missing billing months.
  - `ag-scope3-supply`: Freight logistics (tonne-km) and spend-based procurement proxy extraction.
  - `ag-mitigation-quota`: Decree 06/2022/NĐ-CP & Decree 119/2025/NĐ-CP Mẫu 02 facility mitigation and quota surplus/deficit accounting.
  - `ag-synthesizer`: Official Vietnamese regulatory GHG disclosure and executive roadmap generation.
- **Non-blocking Dual-Logging Engine (`runs/<run_id>/intermediate/`)**:
  - `query_log.json`: Logs anomalies, missing billing periods, and low-confidence proxy usages for human auditor verification.
  - `assumption_log.json`: Documents conservative IPCC/TCVN estimation assumptions and records data reliability confidence score deductions.
- **Decree 06/2022/NĐ-CP Mẫu 02 Mitigation Math Engine (`ecostream/engine/mitigation_math.py`)**:
  - Exact facility emission reduction calculations ($GPT = PT_{CS} - PT$).
  - Emission quota surplus/deficit tracking ($Quota_{\text{alloc}} - PT$).
  - Word (`.docx`) table export adhering strictly to Phụ lục IV Mẫu 02.
- **Dedicated Live Workflow Monitoring Dashboard (`ecostream/app/static/monitor.html` & `monitor.js`)**:
  - Standalone pure HTML/JavaScript monitoring interface at `/monitor`.
  - Configurable real-time polling engine (default 3s) with Play/Pause controls and countdown timer.
  - Run selector dropdown and path input to inspect any historical or active run in `runs/`.
  - 5-Phase Lifecycle Stepper visualizer showing current progress, timestamp, and duration.
  - Tabbed Intermediate JSON Inspector for Scope 1, Scope 2, Scope 3, Mẫu 02, Query Log, Assumption Log, Index, and State.
  - Deliverables panel with one-click download for Markdown, HTML, DOCX, PDF, and JSON.
- **Claude Code Native Subagents, Skills & Workflow (`.claude/`)**:
  - Defined subagent configurations in `.claude/agents/*.md` configured with `model: agy/gemini-3.7-flash-low`.
  - Skills for interactive execution: `/ecostream`, `/mitigation`, `/audit`.
  - Dynamic multi-agent workflow script in `.claude/workflows/wf-ecostream.js`.
- **Deliverable Templates & Multi-format Exporters (`ecostream/reporting/`)**:
  - `Bao_cao_kiem_ke_va_giam_nhe_KNK.md`
  - `Bao_cao_kiem_ke_va_giam_nhe_KNK.html`
  - `Bao_cao_Mau02_ND06.docx`
  - `Bao_cao_kiem_ke_va_giam_nhe_KNK.pdf`
  - `final_inventory_summary.json`
- **Expanded Automated Test Suite (35 Unit & Integration Tests)**:
  - `test_markitdown_ingestion.py`: Universal ingestion and SHA-256 caching tests.
  - `test_mitigation_math.py`: Mẫu 02 mitigation math and quota tests.
  - `test_monitor_api.py`: Monitor endpoints and intermediate JSON retrieval tests.
  - `test_orchestrator_e2e.py`: Full end-to-end multi-agent pipeline tests.
  - `test_query_assumption_logs.py`: Data imputation, anomaly logging, and confidence penalty tests.
  - `test_subagents.py`: Domain subagent isolation tests.

#### Changed
- `ecostream/app/server.py`: Added `/monitor`, `/api/orchestrator/runs`, `/api/orchestrator/runs/{run_id}`, `/api/orchestrator/runs/{run_id}/files`, and `/api/orchestrator/runs/{run_id}/intermediate/{filename}` endpoints.
- `ecostream/cli.py`: Updated CLI to support multi-agent pipeline arguments (`--input`, `--company`, `--facility`, `--year`, `--demo`).
- `ecostream/engine/reliability.py`: Enhanced 5-dimensional scoring model to penalize spend proxies and apply deductions from assumption logs.
- `ecostream/factors/database.py`: Added helper lookup methods (`get_all_factors()`, `list_factors()`) for API and subagent consumption.
- `tests/test_pipeline.py`: Realigned benchmark tests with the new multi-agent inventory baseline ($4,945.05\text{ tCO}_2\text{e}$).

---

## [0.1.0] - 2026-09-12

### Initial Release: EcoStream Proof of Concept
- Core 5-dimensional data reliability engine (`Completeness`, `Temporal`, `Geographical`, `Source`, `Extraction`).
- Scope 1, Scope 2, Scope 3 deterministic calculator with Gaussian 95% Confidence Interval error propagation.
- Basic regex-based document parsers for EVN bills, Petrolimex invoices, freight logistics CSVs, and supplier spend tables.
- Interactive Web Dashboard (`FastAPI` + `Chart.js` + `Bootstrap 5`).
- Initial Vietnamese and English reporting exporters (`Markdown`, `HTML`, `PDF`).
