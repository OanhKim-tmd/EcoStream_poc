# 🌱 EcoStream — AI-Powered Carbon Accounting & Data Reliability Engine

> **Dịch vụ tư vấn và phân tích phát thải carbon được hỗ trợ bởi nền tảng AI**  
> *Dự án tham dự Cuộc thi Sáng tạo USTH 2026 (Inno-Inspiration USTH 2026)*  
> Tác giả: **Vũ Thị Kim Oanh** (Data Science, USTH)

---

## 📌 Bối Cảnh & Vấn Đề Giải Quyết

Từ **01/01/2026**, Liên minh Châu Âu chính thức áp dụng cơ chế **CBAM** (Carbon Border Adjustment Mechanism). Tại Việt Nam, hơn 3.000 doanh nghiệp cũng thuộc diện bắt buộc kiểm kê khí nhà kính theo **Nghị định 06/2022/NĐ-CP**.

Tuy nhiên, phần lớn các doanh nghiệp vừa và nhỏ (SME) Việt Nam:
- **Dữ liệu phân tán, không đồng nhất**: Hóa đơn tiền điện EVN, hóa đơn xăng dầu Petrolimex, phiếu xuất kho giao nhận và bảng chi phí kế toán rời rạc.
- **Khoảng trống Scope 3**: Thiếu số liệu đo đếm vật lý (tấn-km, kg vật liệu), dẫn đến việc phải ước tính gián tiếp dựa trên số tiền (Spend-based proxy) với sai số rất cao ($\pm 40\%$).
- **Thiếu tính truy nguyên (Audit Lineage)**: Các công cụ tính toán truyền thống chỉ đưa ra một con số $\text{CO}_2$ vô hồn mà không thể chứng minh nguồn gốc cho đơn vị kiểm toán quốc tế.

### 💡 Giải Pháp Của EcoStream
EcoStream không cạnh tranh đơn thuần như một chiếc máy tính carbon. EcoStream tập trung vào:
1. **Lớp Bằng Chứng (Evidence & Provenance Layer)**: Truy vết từng dòng phát thải về tài liệu và số dòng/ảnh trích xuất gốc.
2. **Bộ Đo 5 Chiều Độ Tin Cậy (Reliability Engine)**: Đánh giá Tính đầy đủ, Đồng bộ thời gian, Đặc thù địa phương (Hệ số MONRE/Việt Nam), Chất lượng nguồn dữ liệu và Độ tin cậy trích xuất AI.
3. **Lộ Trình Hành Động ("What Should I Improve?")**: Chỉ rõ cho doanh nghiệp cần thu thập bổ sung chứng từ nào để nâng cấp điểm tin cậy dữ liệu lên mức **Audit-Ready (Grade A)**.

---

## 🏗 Kiến Trúc Kỹ Thuật (5-Stage Pipeline)

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌───────────────────┐     ┌─────────────────────┐
│ 1. Ingestion    │ ──> │ 2. Extraction &  │ ──> │ 3. Quality &     │ ──> │ 4. Carbon Engine  │ ──> │ 5. Decision &      │
│ Messy Invoices, │     │ Evidence Layer   │     │ Reliability      │     │ Scope 1, 2, 3     │     │ Actionable Feedback │
│ Bills, Excel    │     │ (OCR/LLM + audit)│     │ (5-dim scoring)  │     │ + Uncertainty     │     │ Hotspots & Roadmap  │
└─────────────────┘     └──────────────────┘     └──────────────────┘     └───────────────────┘     └─────────────────────┘
```

1. **Ingestion Layer** (`ecostream/ingestion`): Tiếp nhận đa định dạng (hóa đơn văn bản, text OCR từ PDF, bảng kê CSV, hóa đơn tiền điện EVN).
2. **Extraction & Evidence Layer** (`ecostream/extraction`): Bộ phân tích quy tắc chuyên sâu kết hợp adapter AI trích xuất sản lượng hoạt động, đơn vị tính, kèm bằng chứng (snippet + line).
3. **Reliability Engine** (`ecostream/engine/reliability.py`): Đánh giá 5 chiều chất lượng dữ liệu:
   - *Completeness* ($25\%$)
   - *Temporal Alignment* ($15\%$)
   - *Geographical Fit* ($20\%$) — Ưu tiên hệ số MONRE Việt Nam
   - *Source Reliability* ($25\%$) — Phạt nặng Spend-based proxy
   - *Extraction Confidence* ($15\%$)
4. **Carbon Engine & Uncertainty Propagation** (`ecostream/engine/calculator.py`): Tính toán theo chuẩn GHG Protocol (Scope 1, 2, 3) và lan truyền sai số thống kê $95\%$ Confidence Interval:
   $$\sigma_{\text{total}} = \sqrt{\sum \sigma_i^2}$$
5. **Decision & Roadmap Advisor** (`ecostream/engine/advisor.py`): Nhận diện điểm nóng phát thải và đề xuất hành động cụ thể cho SME.

---

## 🚀 Hướng Dẫn Cài Đặt & Khởi Chạy

### 1. Cài đặt môi trường
Yêu cầu Python 3.10+ (Đã thử nghiệm trên Python 3.14).
```bash
# Cài đặt các thư viện cần thiết
pip install -r requirements.txt
# hoặc
pip install fastapi uvicorn rich pydantic
```

### 2. Chạy Demo trên Giao Diện Web (FastAPI + Dashboard)
Khởi động máy chủ web cục bộ:
```bash
python -m ecostream.app
```
Mở trình duyệt truy cập: **`http://localhost:8080`**

Các tính năng trên giao diện:
- **⚡ Chạy Demo (EcoGarment Vietnam)**: Tải và xử lý toàn bộ bộ dữ liệu mẫu SME (điện EVN, dầu Petrolimex, vận tải, mua hàng).
- **Biểu đồ phân bổ Scope 1, 2, 3 & Độ tin cậy 5 chiều**: Trực quan hóa tương tác qua Chart.js.
- **Lớp bằng chứng (Evidence Table)**: Xem chi tiết từng dòng tính toán, trích xuất tài liệu gốc và sai số.
- **Lộ trình "What Should I Improve?"**: Gợi ý các chứng từ cần bổ sung để tối ưu độ tin cậy.
- **📤 Tải lên chứng từ mới**: Hỗ trợ upload hóa đơn và bảng kê thực tế của doanh nghiệp.
- **📄 In / Xuất báo cáo kiểm toán**: Định dạng HTML và Markdown chuẩn mực.

### 3. Chạy qua Giao Diện Dòng Lệnh (CLI)
Chạy trực tiếp quy trình kiểm kê và xuất báo cáo:
```bash
python -m ecostream.cli --demo
```
Kết quả báo cáo sẽ được tự động xuất ra:
- `report_audit.md` (Báo cáo Markdown)
- `report_audit.html` (Báo cáo HTML độc lập có thể in)

---

## 🧪 Chạy Kiểm Thử Tự Động (Automated Tests)

Chạy toàn bộ 13 bài kiểm thử đơn vị & tích hợp:
```bash
python -m unittest discover tests/ -v
```

Bộ test bao gồm:
- `test_calculator.py`: Kiểm tra tính toán Scope 1, 2, 3 và độ bất định theo hệ số MONRE / IPCC.
- `test_reliability.py`: Kiểm tra thuật toán chấm điểm 5 chiều và xếp hạng Audit-Ready.
- `test_extraction.py`: Kiểm tra khả năng trích xuất chính xác hóa đơn EVN, Petrolimex, bảng kê logistics.
- `test_pipeline.py`: Kiểm tra tích hợp toàn trình API FastAPI và tính năng xuất báo cáo.

---

## 📊 Bộ Dữ Liệu Kiểm Thử Mẫu (Benchmark SME)

Trong thư mục `data/samples/`:
- `sample_evn_bill.txt`: Hóa đơn tiền điện EVN Hà Nội (45,250 kWh, trạm chuyên dùng 560kVA).
- `sample_fuel_invoice.txt`: Hóa đơn điện tử Petrolimex (1,850 lít dầu DO 0.05S).
- `sample_freight_log.csv`: Bảng kê 5 chuyến vận chuyển container & xe tải liên tỉnh (tấn, km, tuyến đường).
- `sample_supplier_spend.csv`: Sổ chi mua hàng kết hợp dữ liệu vật lý (carton, túi PE, vải cotton) và dữ liệu chi phí ước tính gián tiếp (Spend proxy) để chứng minh khoảng trống dữ liệu thực tế của SME.