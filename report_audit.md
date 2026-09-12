# BÁO CÁO KIỂM KÊ PHÁT THẢI KHÍ NHÀ KÍNH & ĐỘ TIN CẬY DỮ LIỆU
### EcoStream AI Carbon Engine — Audit & Reliability Disclosure

- **Doanh nghiệp**: EcoGarment Vietnam JSC
- **Địa điểm / Cơ sở**: Nam Thang Long IP, Hanoi, Vietnam
- **Lĩnh vực hoạt động**: Garment & Textile Manufacturing
- **Kỳ báo cáo**: Tháng 03/2026
- **Ngày phát hành**: 2026-09-12 22:53:36
- **Mã báo cáo**: `ECO-RPT-20260912-2253`

---

## 1. TỔNG QUAN PHÁT THẢI (EXECUTIVE SUMMARY)

| Chỉ số | Giá trị | Đơn vị | Ghi chú / Biên độ tin cậy |
| :--- | :---: | :---: | :--- |
| **Tổng phát thải ròng** | **89.379** | **tCO₂e** | Khoảng tin cậy 95%: [79.688 - 99.070] tCO₂e |
| • **Scope 1 (Trực tiếp)** | 4.958 | tCO₂e | Nhiên liệu đốt lò hơi & máy phát dự phòng |
| • **Scope 2 (Gián tiếp điện)** | 32.675 | tCO₂e | Điện lưới quốc gia EVN (Hệ số MONRE) |
| • **Scope 3 (Chuỗi giá trị)** | 51.746 | tCO₂e | Vận tải, nguyên vật liệu & bao bì |
| **Chỉ số tin cậy EcoStream** | **89.0%** | **Grade A** | **Audit-Ready (Sẵn sàng kiểm toán CBAM / ESG)** |

### Nhận định độ tin cậy dữ liệu:
> Dữ liệu có độ tin cậy rất cao, truy xuất nguồn gốc rõ ràng và sử dụng hệ số phát thải đặc thù Việt Nam.

---

## 2. ĐÁNH GIÁ 5 CHIỀU ĐỘ TIN CẬY DỮ LIỆU (RELIABILITY RADAR)

| Tiêu chí đánh giá | Điểm số | Xếp loại | Ý nghĩa & Tiêu chuẩn áp dụng |
| :--- | :---: | :---: | :--- |
| **Tính đầy đủ (Completeness)** | 85.4% | Grade A | Mức độ đầy đủ của các trường thông tin bắt buộc (sản lượng, đơn vị tính, chu kỳ thời gian). |
| **Đồng bộ thời gian (Temporal Alignment)** | 98.3% | Grade A | Độ khớp thời gian của chứng từ đối với kỳ báo cáo (tháng/năm). |
| **Tính đặc thù địa phương (Geographical Fit)** | 92.9% | Grade A | Mức độ sử dụng hệ số phát thải cụ thể của Việt Nam (Lưới điện MONRE, xăng dầu TCVN) thay vì chỉ số toàn cầu. |
| **Chất lượng nguồn dữ liệu (Source Reliability)** | 80.8% | Grade B | Tỷ trọng dữ liệu sơ cấp đo đếm (công tơ, hóa đơn điện tử) so với các ước tính gián tiếp dựa trên chi phí. |
| **Độ tin cậy trích xuất AI (Extraction Confidence)** | 94.2% | Grade A | Độ chuẩn xác và bằng chứng số dòng/ảnh chụp khi trích xuất dữ liệu tự động từ tài liệu. |

- **Tỷ trọng dữ liệu sơ cấp đo đếm (Primary Data)**: 41.7%
- **Tỷ trọng dữ liệu ước tính gián tiếp (Spend-based Proxy)**: 16.7%

---

## 3. BẢNG TRUY NGUYÊN CHỨNG TỪ & HỆ SỐ PHÁT THẢI (EVIDENCE & PROVENANCE LAYER)

| STT | Hoạt động | Phạm vi | Lượng hoạt động | Hệ số (EF) | Phát thải (tCO₂e) | Sai số | Nguồn chứng từ gốc | Trích xuất | Tin cậy |
| :---: | :--- | :---: | :---: | :--- | :---: | :---: | :--- | :---: | :---: |
| 1 | EVN Grid Electricity Consumption (Kỳ 03/2026) | Scope 2 | 45,250.00 kWh | 0.7221 (Vietnam National Electricity G...) | **32.675** | ±5.0% | `sample_evn_bill.txt` (THÔNG SỐ ĐO ĐẾM VÀ SẢN LƯỢNG ĐIỆN NĂNG TIÊU THỤ:) | RULE_BASED_EVN | 99.7% |
| 2 | Road Freight: Hà Nội - Cảng Hải Phòng (Xuất khẩu) (14.2t x 125.0km) | Scope 3 | 1,775.00 ton-km | 0.096 (Road Freight Transport (Vận ch...) | **0.170** | ±15.0% | `sample_freight_log.csv` (Row 2) | CSV_TABULAR_PARSER | 93.0% |
| 3 | Road Freight: Nam Định - Hà Nội (Nhập vải thô) (7.5t x 95.0km) | Scope 3 | 712.50 ton-km | 0.096 (Road Freight Transport (Vận ch...) | **0.068** | ±15.0% | `sample_freight_log.csv` (Row 3) | CSV_TABULAR_PARSER | 93.0% |
| 4 | Road Freight: Hà Nội - Cảng Hải Phòng (Lô hàng 2) (18.0t x 125.0km) | Scope 3 | 2,250.00 ton-km | 0.096 (Road Freight Transport (Vận ch...) | **0.216** | ±15.0% | `sample_freight_log.csv` (Row 4) | CSV_TABULAR_PARSER | 93.0% |
| 5 | Road Freight: Bắc Ninh - Hà Nội (Nhập phụ liệu) (2.8t x 42.0km) | Scope 3 | 117.60 ton-km | 0.096 (Road Freight Transport (Vận ch...) | **0.011** | ±15.0% | `sample_freight_log.csv` (Row 5) | CSV_TABULAR_PARSER | 93.0% |
| 6 | Road Freight: Hà Nội - Nội Bài (Hàng mẫu bay) (0.4t x 35.0km) | Scope 3 | 14.00 ton-km | 0.096 (Road Freight Transport (Vận ch...) | **0.001** | ±15.0% | `sample_freight_log.csv` (Row 6) | CSV_TABULAR_PARSER | 93.0% |
| 7 | Diesel Fuel (Dầu DO 0.05S) - CÔNG TY XĂNG DẦU KHU VỰC I - TNHH MTV | Scope 1 | 1,850.00 liter | 2.68 (Diesel Fuel Combustion (Dầu DO...) | **4.958** | ±7.5% | `sample_fuel_invoice.txt` (Line 22) | RULE_BASED_FUEL | 96.9% |
| 8 | Purchased Materials: Thùng carton 5 lớp đóng gói xuất khẩu | Scope 3 | 3,400.00 kg | 0.94 (Corrugated Cardboard Packaging...) | **3.196** | ±15.0% | `sample_supplier_spend.csv` (Row 2) | CSV_TABULAR_PARSER | 91.1% |
| 9 | Purchased Materials: Túi nilon PE bảo quản quần áo may mặc | Scope 3 | 550.00 kg | 2.45 (LDPE Plastic Wrapping & Polyba...) | **1.347** | ±20.0% | `sample_supplier_spend.csv` (Row 3) | CSV_TABULAR_PARSER | 91.1% |
| 10 | Purchased Materials: Vải dệt thô Cotton 100% nhập xưởng | Scope 3 | 4,200.00 kg | 8.3 (Raw Cotton Textile Material (V...) | **34.860** | ±25.0% | `sample_supplier_spend.csv` (Row 4) | CSV_TABULAR_PARSER | 91.1% |
| 11 | Spend-based Estimate: Chi phí thuê ngoài xe trung chuyển linh hoạt | Scope 3 | 28,500,000.00 VND | 0.00025 (Spend-based Freight Proxy (Ước...) | **7.125** | ±45.0% | `sample_supplier_spend.csv` (Row 5) | CSV_FALLBACK_SPEND | 66.8% |
| 12 | Spend-based Estimate: Chi phí vật tư phụ kiện và phụ liệu dệt may nhỏ lẻ | Scope 3 | 19,000,000.00 VND | 0.00025 (Spend-based Freight Proxy (Ước...) | **4.750** | ±45.0% | `sample_supplier_spend.csv` (Row 6) | CSV_FALLBACK_SPEND | 66.8% |

---

## 4. 'WHAT SHOULD I IMPROVE?' — LỘ TRÌNH NÂNG CẤP DỮ LIỆU & GIẢM PHÁT THẢI

### 📍 [HIGH] Nâng cấp dữ liệu vận tải & mua hàng từ chi phí (VNĐ) sang số liệu vật lý
- **Phạm vi tác động**: Scope 3 (DATA_QUALITY_UPGRADE)
- **Hiện trạng & Khoảng trống**: Đang có 2 hạng mục (11.88 tCO2e, chiếm 13.3%) sử dụng hệ số ước tính theo số tiền (Spend-based proxy) với sai số lên tới ±40%.
- **Hành động đề xuất cho SME**: Yêu cầu nhà xe/đơn vị logistics cung cấp bảng kê quãng đường (km) và khối lượng hàng (tấn); yêu cầu nhà cung cấp vật liệu ghi rõ số kg trên hóa đơn VAT thay vì chỉ ghi tổng tiền dịch vụ.
- **Tiềm năng gia tăng độ tin cậy**: **+14.5%**

### 📍 [HIGH] Tối ưu phát thải điện lưới (Scope 2 Hotspot)
- **Phạm vi tác động**: Scope 2 (DECARBONIZATION_ROADMAP)
- **Hiện trạng & Khoảng trống**: Điện lưới quốc gia chiếm tới 36.6% tổng phát thải doanh nghiệp (32.67 tCO2e). Hệ số phát thải lưới điện Việt Nam (0.7221 kg CO2/kWh) là nguồn phát thải chủ chốt.
- **Hành động đề xuất cho SME**: 1. Kiểm toán năng lượng hệ thống máy nén khí, động cơ công nghiệp và chiếu sáng LED.
2. Xem xét mô hình đầu tư điện mặt trời mái nhà (Rooftop Solar) tự dùng để giảm trực tiếp lượng kWh mua từ EVN.
- **Tiềm năng gia tăng độ tin cậy**: **+5.0%**

### 📍 [MEDIUM] Chuẩn hóa nhật ký tiêu hao nhiên liệu máy phát và phương tiện
- **Phạm vi tác động**: Scope 1 (DATA_QUALITY_UPGRADE)
- **Hiện trạng & Khoảng trống**: Phát thải trực tiếp Scope 1 đạt 4.96 tCO2e. Hiện đã có hóa đơn nhiên liệu Petrolimex nhưng chưa có nhật ký phân tách giờ chạy máy phát và định mức tiêu hao từng xe.
- **Hành động đề xuất cho SME**: Số hóa sổ giao nhận nhiên liệu nội bộ, ghi nhận số giờ chạy máy phát điện dự phòng và số km công tơ mét từng xe hàng tháng để giám sát định mức tiêu hao.
- **Tiềm năng gia tăng độ tin cậy**: **+6.0%**

---

*Báo cáo được tổng hợp tự động bởi EcoStream Engine v0.1.0 — Phục vụ tuân thủ CBAM & Nghị định 06/2022/NĐ-CP.*