# 🌱 EcoStream — AI Multi-Agent Carbon Accounting, Mẫu 02 Mitigation & Reliability Engine

> **Dịch vụ tư vấn và phân tích phát thải carbon được hỗ trợ bởi nền tảng Multi-Agent AI**  
> *Dự án tham dự Cuộc thi Sáng tạo USTH 2026 (Inno-Inspiration USTH 2026)*  
> Tác giả: **Vũ Thị Kim Oanh** (Data Science, USTH)

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Subagents%20%26%20Workflows-6b46c1.svg)](https://code.claude.com)
[![Tests](https://img.shields.io/badge/tests-35%20passed-brightgreen.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📌 Bối Cảnh & Vấn Đề Giải Quyết

Từ **01/01/2026**, Liên minh Châu Âu (EU) chính thức áp dụng cơ chế đánh thuế carbon qua biên giới **CBAM** (*Carbon Border Adjustment Mechanism*). Tại Việt Nam, hơn 3.000 cơ sở phát thải trọng điểm bắt buộc phải thực hiện kiểm kê khí nhà kính (KNK) và lập kế hoạch giảm nhẹ phát thải định kỳ theo **Nghị định 06/2022/NĐ-CP**, **Nghị định 119/2025/NĐ-CP**, và các Quyết định **01/2022/QĐ-TTg**, **13/2024/QĐ-TTg**.

### Thách Thức Thực Tế Của Doanh Nghiệp (SME / Nhà máy)
1. **Dữ liệu thực tế phân tán, dị cấu trúc**: Hóa đơn tiền điện EVN, hóa đơn dầu Petrolimex, bảng kê vận chuyển logistics (tấn-km), bảng chi phí mua hàng SAP/MISA, chứng chỉ I-REC và phiếu đo đếm lò hơi không theo một biểu mẫu cố định.
2. **Khoảng trống Scope 3 & Dữ liệu gián tiếp**: Thiếu dữ liệu đo đếm vật lý, phải sử dụng ước tính theo chi phí (*Spend-based proxy*) dẫn đến độ bất định cao ($\pm 40\%$).
3. **Tuân thủ quy định giảm nhẹ phát thải Mẫu 02**: Tính toán giảm phát thải ($GPT = PT_{CS} - PT$) và hạn ngạch phát thải ($Quota_{\text{alloc}} - PT$) đòi hỏi phương pháp luận chặt chẽ, dễ bị kiểm toán truy vấn.
4. **Thiếu khả năng giám sát quy trình xử lý**: Doanh nghiệp không thể theo dõi dữ liệu trung gian khi chạy các pipeline xử lý AI phức tạp.

---

## 💡 Giải Pháp Đột Phá Của EcoStream

EcoStream là nền tảng **Multi-Agent AI Orchestrator** kết hợp **Toán học Tất định 100% (Deterministic Math)** và **Bảng thông tin Trạng thái (Blackboard Architecture)**:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│                             ECOSTREAM MULTI-AGENT ARCHITECTURE                                │
│                                                                                                │
│  [ Input Business Files ] (Excel, PDF Invoices, Word, CSV)                                     │
│            │                                                                                   │
│            ▼                                                                                   │
│  [ Microsoft MarkItDown + SHA-256 Ingestion Cache ] ──> Modular Markdown Inputs                │
│            │                                                                                   │
│            ▼                                                                                   │
│  [ ag-discovery Agent ] ──> Schema Discovery & Task Routing (index.json)                       │
│            │                                                                                   │
│    ┌───────┴───────────────────────────────┬───────────────────────────────┐                   │
│    ▼                                       ▼                               ▼                   │
│ [ ag-scope1-fuel ]                [ ag-scope2-power ]             [ ag-scope3-supply ]         │
│ Direct Combustion                 EVN Grid + Seasonal             Logistics & Spend-Based      │
│ & LPG Cylinders                   Interpolation                   Procurement Proxies          │
│    │                                       │                               │                   │
│    └───────────────────────┬───────────────┴───────────────────────────────┘                   │
│                            ▼                                                                   │
│                 [ ag-mitigation-quota ]                                                        │
│                 Decree 06/2022 Mẫu 02 Math ($GPT = PT_{CS} - PT$)                              │
│                 Facility Mitigation & Emission Quota Surpluses/Deficits                        │
│                            │                                                                   │
│                            ▼                                                                   │
│                 [ Non-blocking Dual-Logging Engine ]                                           │
│                 ├── query_log.json      (Human Verification Flags)                             │
│                 └── assumption_log.json (Audit Assumptions & Confidence Deductions)            │
│                            │                                                                   │
│                            ▼                                                                   │
│                 [ Deterministic Python Math & Gaussian Uncertainty Engine ]                    │
│                 $E = Q \times EF$   |   $\sigma_{\text{total}} = \sqrt{\sum \sigma_i^2}$       │
│                            │                                                                   │
│                            ▼                                                                   │
│                 [ ag-synthesizer Agent ]                                                       │
│                 Official Vietnamese Regulatory GHG Disclosures & Hotspot Roadmaps              │
│                            │                                                                   │
│                            ▼                                                                   │
│  [ Deliverables ] ──> .MD, .HTML, .DOCX (Mẫu 02), .PDF, summary.json                           │
│  [ Live Monitor ] ──> Real-time Polling Dashboard at /monitor                                  │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🌟 Các Tính Năng Cốt Lõi

### 1. Ingestion Toàn Năng (Universal Ingestion & SHA-256 Cache)
- Sử dụng **Microsoft MarkItDown** chuyển đổi mọi bảng tính Excel nhiều sheet (`.xlsx`), hóa đơn PDF, văn bản Word (`.docx`), và file `.csv` sang định dạng Markdown chuẩn.
- Tự động tách từng sheet thành các file Markdown độc lập (`input_NhienLieu_Scope1.md`, `input_DienLuoi_EVN_Scope2.md`, v.v.).
- Cơ chế **SHA-256 Fingerprint Caching** bỏ qua việc đọc lại các file đã xử lý, tối ưu hoá thời gian và tài nguyên.

### 2. Hệ Thống Subagent Chuyên Ngành (Specialized Domain Subagents)
Các subagent được cấu hình độc lập với prompt chuyên sâu và hoạt động theo quy trình Blackboard:
- **`ag-discovery`**: Nhận diện cấu trúc tài liệu, phân loại nguồn phát thải và lập bảng định tuyến `index.json`.
- **`ag-scope1-fuel`**: Trích xuất dữ liệu đốt nhiên liệu trực tiếp (dầu DO/FO, xăng, than đá, khí LPG). Tự động quy đổi đơn vị đóng gói (bình LPG $12\text{kg}, 45\text{kg} \to \text{tấn}$).
- **`ag-scope2-power`**: Trích xuất hóa đơn điện lưới EVN 3 giá (Cao điểm, Bình thường, Thấp điểm). Tự động áp dụng **Nội suy Tuyến tính Theo mùa (Seasonal Linear Interpolation)** khi phát hiện thiếu tháng hóa đơn.
- **`ag-scope3-supply`**: Xử lý logistics chuỗi cung ứng (tấn-km theo loại xe tải/container) và phân tích chi phí mua hàng bằng hệ số phát thải theo ngành EXIOBASE.
- **`ag-mitigation-quota`**: Chuyên trách kiểm kê giảm nhẹ phát thải theo **Nghị định 06/2022/NĐ-CP Mẫu 02**, tính toán lượng giảm phát thải so với đường cơ sở và cân đối hạn ngạch phát thải.
- **`ag-synthesizer`**: Tổng hợp toàn bộ kết quả, đối chiếu quy chuẩn Việt Nam và lập báo cáo phát thải chính thức bằng tiếng Việt.

### 3. Cơ Chế Nhật Ký Kép Bất Đồng Bộ (Query Log & Assumption Log)
Để không làm gián đoạn pipeline khi dữ liệu thực tế bị thiếu hoặc có lỗi:
- **`query_log.json`**: Ghi nhận các điểm nghi vấn dữ liệu (thiếu hóa đơn tháng, số liệu bất thường, áp dụng giả định ước tính) để kiểm toán viên hoặc quản lý nhà máy hậu kiểm.
- **`assumption_log.json`**: Lưu trữ chi tiết các giả định bảo thủ (Conservative Assumptions) theo IPCC/TCVN được áp dụng, kèm theo mức trừ điểm tin cậy tương ứng.

### 4. Động Cơ Tính Toán Tất Định & Lan Truyền Sai Số Gaussian
- **100% Deterministic Math**: Mọi phép tính phát thải $E = Q \times EF$ và giảm phát thải $GPT = PT_{CS} - PT$ được thực thi bằng mã Python thuần, không phụ thuộc vào suy luận số học của LLM.
- **Hệ số phát thải chuẩn**: Tích hợp cơ sở dữ liệu hệ số phát thải từ Bộ TN&MT (Quyết định 2626/QĐ-BTNMT, Thông tư 17/2022/TT-BTNMT) và IPCC EFDB.
- **Lan truyền sai số Gaussian 95% Confidence Interval**:
  $$\sigma_{\text{total}} = \sqrt{\sum_{i=1}^n \sigma_i^2}$$
  Xác định khoảng tin cậy phát thải $[E_{\text{total}} - 1.96\sigma_{\text{total}}, E_{\text{total}} + 1.96\sigma_{\text{total}}]$.

### 5. Giao Diện Giám Sát Quy Trình Trực Tiếp (Live Workflow Monitor)
Truy cập tại **`http://localhost:8080/monitor`**:
- **Bộ điều khiển Polling thời gian thực**: Tự động thăm dò trạng thái thư mục `runs/<run_id>/` mỗi $X$ giây (mặc định 3 giây), có nút Play/Pause và thanh đếm nhịp.
- **Bộ chọn Run tương tác**: Danh sách dropdown hiển thị đầy đủ các lần chạy với ID, thời gian, trạng thái, tiến độ %.
- **5-Phase Lifecycle Stepper**: Hiển thị trực quan từng giai đoạn (Ingestion $\to$ Discovery $\to$ Extraction $\to$ Math & Mitigation $\to$ Synthesis).
- **Tabbed Intermediate JSON Inspector**: Khám phá trực tiếp dữ liệu trích xuất Scope 1, Scope 2, Scope 3, Mẫu 02, Query Log, Assumption Log, Index và State thô.
- **Quản lý & Tải về Deliverables**: Xem trước và tải ngay các file báo cáo Markdown, HTML, Word DOCX, PDF, JSON.

---

## 📂 Cấu Trúc Dự Án

```
ecostream-poc/
├── .claude/                             # Claude Code Subagents, Skills & Workflows
│   ├── agents/                          # Cấu hình Subagent chuyên ngành (.md)
│   │   ├── ag-discovery.md
│   │   ├── ag-scope1-fuel.md
│   │   ├── ag-scope2-power.md
│   │   ├── ag-scope3-supply.md
│   │   ├── ag-mitigation-quota.md
│   │   └── ag-synthesizer.md
│   ├── skills/                          # Lệnh Claude Code Skill
│   │   ├── ecostream/SKILL.md           # Lệnh /ecostream
│   │   ├── mitigation/SKILL.md          # Lệnh /mitigation
│   │   └── audit/SKILL.md               # Lệnh /audit
│   ├── workflows/                       # Kịch bản Workflow động
│   │   └── wf-ecostream.js              # Multi-agent dynamic pipeline script
│   └── references/                      # Tài liệu pháp lý tham chiếu (NĐ 06, NĐ 119)
├── ecostream/                           # Core Python Package
│   ├── agents/                          # Logic thực thi Python Subagent
│   │   ├── discovery.py
│   │   ├── scope1.py
│   │   ├── scope2.py
│   │   ├── scope3.py
│   │   ├── mitigation.py
│   │   └── synthesizer.py
│   ├── app/                             # FastAPI Web Server & Dashboard
│   │   ├── server.py                    # Web API & Monitor endpoints
│   │   └── static/
│   │       ├── index.html               # Carbon & Reliability Dashboard
│   │       ├── monitor.html             # Live Workflow Monitor HTML
│   │       └── monitor.js               # Reactive Polling & UI Engine
│   ├── engine/                          # Động cơ tính toán tất định
│   │   ├── calculator.py                # Scope 1, 2, 3 & Uncertainty Math
│   │   ├── mitigation_math.py           # NĐ 06/2022 Mẫu 02 Mitigation Math
│   │   ├── reliability.py               # 5-Dimension Reliability Scoring
│   │   └── advisor.py                   # Emission Hotspot & Action Roadmap
│   ├── factors/                         # CSDL Hệ số phát thải
│   │   ├── database.py                  # MONRE & IPCC Factor Database
│   │   └── default_factors.json
│   ├── ingestion/                       # Module tiếp nhận & chuyển đổi dữ liệu
│   │   ├── markitdown_loader.py         # Microsoft MarkItDown Universal Loader
│   │   └── cache.py                     # SHA-256 Fingerprint Cache
│   ├── models/                          # Pydantic Schemas & State Models
│   │   ├── state.py                     # Blackboard Workspace State & Index
│   │   ├── mitigation.py                # Mẫu 02 Mitigation & Quota Schemas
│   │   └── results.py                   # Carbon Inventory & Audit Schemas
│   ├── orchestrator/                    # Bộ điều phối Pipeline
│   │   ├── pipeline.py                  # WorkflowOrchestrator
│   │   └── state.py                     # BlackboardWorkspace Manager
│   ├── reporting/                       # Xuất báo cáo đa định dạng
│   │   ├── export.py                    # Markdown, HTML, PDF, DOCX Exporter
│   │   └── templates.py                 # Mẫu báo cáo quy chuẩn Việt Nam
│   └── cli.py                           # Command-Line Interface
├── data/samples/                        # Dữ liệu thử nghiệm mẫu (SME Benchmark)
│   └── input.xlsx                       # Multi-tab Excel file benchmark
├── runs/                                # Blackboard Run Workspaces (runs/<run_id>/)
├── scripts/                             # Script sinh dữ liệu thử nghiệm
│   └── generate_mock_excel.py
├── tests/                               # Bộ kiểm thử tự động (35 tests)
├── README.md
├── CHANGELOG.md
└── requirements.txt
```

---

## 🚀 Hướng Dẫn Cài Đặt & Sử Dụng

### 1. Cài đặt Môi trường
Yêu cầu: Python 3.10 trở lên.
```bash
# Clone repository
git clone https://github.com/tmdeptrai/ecostream-poc.git
cd ecostream-poc

# Cài đặt các thư viện phụ thuộc
pip install -r requirements.txt
```

### 2. Sử dụng Giao diện Web & Live Monitor
Khởi động máy chủ web:
```bash
python -m ecostream.app
```
Mở trình duyệt:
- **Dashboard Chính (Interactive Carbon Dashboard)**: `http://localhost:8080`
  - Chạy Demo Benchmark (EcoGarment Vietnam JSC).
  - Tải lên chứng từ tùy chỉnh (Excel, PDF, DOCX, CSV).
  - Xem biểu đồ phát thải, độ tin cậy 5 chiều và lộ trình hành động.
- **Live Workflow Monitor (Giám sát Tiến độ Trực tiếp)**: `http://localhost:8080/monitor`
  - Theo dõi tiến trình 5 giai đoạn thời gian thực.
  - Kiểm tra file trung gian `scope1_extracted.json`, `scope2_extracted.json`, `scope3_extracted.json`, `mitigation_extracted.json`, `query_log.json`, `assumption_log.json`.
  - Xem và tải xuống các báo cáo hoàn chỉnh.

### 3. Sử dụng Giao diện Dòng Lệnh (CLI)
Chạy trực tiếp quy trình kiểm kê và giảm nhẹ phát thải:
```bash
# Chạy bộ dữ liệu Benchmark
python -m ecostream.cli --demo

# Chạy với file hoặc thư mục dữ liệu tùy chỉnh
python -m ecostream.cli --input data/samples/input.xlsx --company "Công ty CP May Mặc EcoGarment" --facility "Nhà máy Hà Nam" --year 2026
```

### 4. Sử dụng trong Claude Code CLI (Skills & Workflows)
Khi sử dụng Claude Code CLI trong thư mục dự án:
- `/ecostream --demo` : Chạy toàn trình pipeline trên bộ dữ liệu mẫu benchmark.
- `/ecostream --input <path>` : Chạy xử lý trên file/thư mục chứng từ chỉ định.
- `/mitigation` : Tính toán bảng giảm nhẹ phát thải Mẫu 02 NĐ 06/2022/NĐ-CP và hạn ngạch.
- `/audit` : Kiểm tra nhật ký nghi vấn dữ liệu (`query_log.json`) và nhật ký giả định (`assumption_log.json`).
- `wf-ecostream` : Kịch bản workflow đa tác nhân điều phối đồng thời các subagents.

---

## 📄 Các Sản Phẩm Đầu Ra (Deliverables)

Mỗi lần chạy sẽ tạo ra thư mục độc lập `runs/<run_id>/deliverables/` chứa đầy đủ các tài liệu quy chuẩn:

| Tên File | Định Dạng | Mô Tả |
| :--- | :--- | :--- |
| `Bao_cao_kiem_ke_va_giam_nhe_KNK.md` | Markdown | Báo cáo kiểm kê khí nhà kính & lộ trình giảm nhẹ toàn diện. |
| `Bao_cao_kiem_ke_va_giam_nhe_KNK.html` | HTML | Báo cáo trình bày chuyên nghiệp, sẵn sàng in ấn hoặc lưu PDF. |
| `Bao_cao_Mau02_ND06.docx` | Word DOCX | Báo cáo kết quả giảm nhẹ phát thải theo đúng **Mẫu 02 Phụ lục IV Nghị định 06/2022/NĐ-CP**. |
| `Bao_cao_kiem_ke_va_giam_nhe_KNK.pdf` | PDF | Báo cáo định dạng PDF phục vụ kiểm toán độc lập. |
| `final_inventory_summary.json` | JSON | Dữ liệu cấu trúc tổng hợp phục vụ tích hợp hệ thống ERP/ESG. |

---

## 🧪 Kiểm Thử Tự Động (Automated Testing)

Chạy toàn bộ 35 bài kiểm thử đơn vị và tích hợp:
```bash
python -m unittest discover tests/ -v
```

### Danh mục Test Suites:
- `test_calculator.py`: Kiểm thử tính toán Scope 1, 2, 3 và lan truyền sai số thống kê.
- `test_reliability.py`: Kiểm thử thuật toán chấm điểm độ tin cậy 5 chiều.
- `test_extraction.py`: Kiểm thử trích xuất hóa đơn điện EVN, xăng dầu Petrolimex, bảng kê vận chuyển.
- `test_markitdown_ingestion.py`: Kiểm thử Microsoft MarkItDown loader và SHA-256 cache.
- `test_mitigation_math.py`: Kiểm thử công thức giảm nhẹ phát thải Mẫu 02 ($GPT = PT_{CS} - PT$) và thặng dư/thiếu hụt hạn ngạch.
- `test_monitor_api.py`: Kiểm thử các API endpoint phục vụ Live Workflow Monitor (`/monitor`, `/runs`, `/files`, `/intermediate`).
- `test_orchestrator_e2e.py`: Kiểm thử luồng tích hợp toàn trình của WorkflowOrchestrator.
- `test_query_assumption_logs.py`: Kiểm thử ghi nhận bất thường, nội suy mùa vụ EVN, quy đổi bình LPG và trừ điểm tin cậy.
- `test_subagents.py`: Kiểm thử hoạt động độc lập của 6 Domain Subagents.
- `test_pipeline.py`: Kiểm thử tích hợp Web Server API và Export endpoints.

---

## 📜 Quy Chuẩn & Pháp Lý Tham Chiếu

1. **Nghị định 06/2022/NĐ-CP** (và NĐ 119/2025/NĐ-CP sửa đổi): Quy định giảm nhẹ phát thải KNK và bảo vệ tầng ô-dôn (Phụ lục IV Mẫu 02).
2. **Quyết định 01/2022/QĐ-TTg & 13/2024/QĐ-TTg**: Danh mục lĩnh vực, cơ sở phát thải KNK phải thực hiện kiểm kê.
3. **Thông tư 17/2022/TT-BTNMT & Quyết định 2626/QĐ-BTNMT**: Quy định kỹ thuật đo đạc, báo cáo, thẩm định (MRV) giảm nhẹ phát thải KNK.
4. **GHG Protocol Corporate Standard & Scope 3 Guidance**: Tiêu chuẩn quốc tế về đo lường và báo cáo phát thải KNK doanh nghiệp.
5. **IPCC 2006/2019 Guidelines for National Greenhouse Gas Inventories**: Hướng dẫn phương pháp luận và hệ số phát thải cơ bản.

---

## 👥 Tác Giả & Bản Quyền

- **Tác giả**: Vũ Thị Kim Oanh (Khoa Khoa học Dữ liệu, Trường Đại học Khoa học và Công nghệ Hà Nội - USTH)
- **Đồ án**: Tham dự *Cuộc thi Sáng tạo USTH 2026 (Inno-Inspiration USTH 2026)*
- **Bản quyền**: Phát hành theo giấy phép mã nguồn mở MIT License.
