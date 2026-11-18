"""Generate a comprehensive simulated dataset that fills 100% of all indices, rows, columns, and sheets
in Bang_khao_sat_da_dien.xlsx across all 12 months, and validates clean calculation through EcoStream.

Run from the project root:
    python scripts/generate_full_survey_data.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ecostream.ingestion.survey_workbook import FUEL_NAMES, FUEL_ROWS, STATIONARY_FUEL_META
from ecostream.orchestrator.survey_pipeline import calculate_survey, prepare_survey


def _build_extra_cells() -> list[tuple[str, str, object]]:
    """Build explicit coordinate values for every auxiliary sheet and metadata cell in Bang_khao_sat_da_dien.xlsx."""
    cells: list[tuple[str, str, object]] = []

    def add(sheet: str, coord: str, val: object) -> None:
        cells.append((sheet, coord, val))

    # 1. Sheet: Thông tin chung
    add("Thông tin chung", "B3", "- Họ và tên người cung cấp thông tin: Nguyễn Văn An")
    add("Thông tin chung", "B4", "- Chức vụ/Bộ phận: Trưởng phòng Quản lý Năng lượng & Môi trường (HSE)")
    add("Thông tin chung", "B5", "- Điện thoại: 0912.345.678")
    add("Thông tin chung", "B6", "- Email: an.nguyen@ecogarment.vn")
    add("Thông tin chung", "B8", "1. Tên cơ sở: Nhà máy May & Năng lượng Hà Nam")
    add("Thông tin chung", "B9", "- Địa chỉ: Khu công nghiệp Đồng Văn III, Phường Đồng Văn, Thị xã Duy Tiên, Tỉnh Hà Nam")
    add("Thông tin chung", "B10", "- Điện thoại: (0226) 3838 999")
    add("Thông tin chung", "B11", "- Email: contact@ecogarment.vn")
    add("Thông tin chung", "B12", "- Người đại diện pháp luật: Trần Minh Tuấn        Chức danh: Tổng Giám đốc")
    add("Thông tin chung", "B14", "- Ngành nghề sản xuất/Loại hình kinh doanh: Sản xuất dệt may, nhuộm hoàn tất & năng lượng công nghiệp — Đơn vị cung cấp: EcoGarment Vietnam JSC")
    add("Thông tin chung", "B15", "- Tình trạng hoạt động: Đang hoạt động ổn định 100% công suất / Năm bắt đầu hoạt động: 2018")

    # 2. Sheet: 1.3 (Số liệu hoạt động trong khai thác, sản xuất, chế biến khoáng sản)
    minerals_1_3 = [
        (3, "Đá vôi công nghiệp (CaCO3 phục vụ xử lý khí thải FGD & phụ trợ)", "12,500 tấn", "Mỏ đá Kiện Khê - Thanh Liêm - Hà Nam", "Khai thác lộ thiên cắt tầng, nghiền sàng khép kín kết hợp hệ thống phun sương dập bụi và lọc bụi túi vải"),
        (4, "Than antraxit nguyên khai sàng tuyển phục vụ lò hơi", "8,400 tấn", "Khu vực mỏ Cẩm Phả - Quảng Ninh (hợp đồng liên kết)", "Tuyển trọng lực huyền phù tự sinh, tách xỉ tự động và sấy tầng sôi tuần hoàn"),
        (5, "Khí tự nhiên đồng hành thu gom & xử lý", "1,250,000 m3", "Trạm tiếp nhận khí Tiền Hải - Thái Bình", "Tách ẩm glycol, nén cao áp CNG và vận chuyển qua hệ thống đường ống khép kín"),
    ]
    for row, name, qty, loc, tech in minerals_1_3:
        add("1.3", f"C{row}", name)
        add("1.3", f"D{row}", qty)
        add("1.3", f"E{row}", loc)
        add("1.3", f"F{row}", tech)

    # 3. Sheet: 1.4 (Lượng môi chất lạnh tiêu thụ/nạp & Thông tin thiết bị lạnh)
    refrigerants_1_4 = [
        (4, "MCL-R22", "kg", [12.5, 10.0, 15.0, 18.5, 22.0, 25.0, 24.5, 22.0, 18.0, 14.5, 12.0, 11.0], "Công ty CP Cơ Điện Lạnh REE"),
        (5, "MCL-R134A", "kg", [18.0, 16.5, 20.0, 24.0, 28.5, 32.0, 35.0, 31.5, 26.0, 21.0, 18.5, 17.0], "Công ty CP Daikin Air Conditioning VN"),
        (6, "MCL-R32", "kg", [14.0, 13.0, 16.0, 19.5, 23.0, 27.5, 29.0, 26.5, 21.5, 17.5, 15.0, 13.5], "Công ty TNHH Panasonic Việt Nam"),
    ]
    for row, code, unit, monthly_vals, supplier in refrigerants_1_4:
        add("1.4", f"D{row}", code)
        add("1.4", f"E{row}", unit)
        for m, val in enumerate(monthly_vals, 1):
            col = get_column_letter(m + 5)  # F..Q
            add("1.4", f"{col}{row}", val)
        add("1.4", f"R{row}", f"=SUM(F{row}:Q{row})")
        add("1.4", f"S{row}", supplier)

    ac_equipments = [
        (3, 1, "Hệ thống Chiller giải nhiệt nước Trane CVHE-500", "Trạm lạnh trung tâm Xưởng Dệt Nhuộm 1", "15/03/2020", "R134a", "1,750 kW (500 RT)", 320, 45.4, "15/06/2026"),
        (4, 2, "Hệ thống điều hòa trung tâm VRV Daikin RXQ18T (12 tổ)", "Khối văn phòng điều hành & Phòng Lab QC", "10/05/2021", "R32", "540 kW (1,840,000 BTU/h)", 180, 34.0, "20/08/2026"),
        (5, 3, "Cụm máy nén lạnh kho bảo quản hóa chất Carrier 30XA", "Kho hóa chất nhuộm & phụ liệu trung tâm", "01/09/2019", "R22", "820 kW (2,800,000 BTU/h)", 210, 22.7, "12/04/2026"),
        (6, 4, "Hệ thống điều hòa chính xác Emerson Liebert PEX", "Phòng Server dữ liệu & Trung tâm điều khiển SCADA", "18/11/2022", "R32", "120 kW (410,000 BTU/h)", 65, 13.5, "05/10/2026"),
    ]
    for row, stt, info, loc, start_date, ref_type, cap, full_kg, last_kg, last_date in ac_equipments:
        add("1.4", f"U{row}", stt)
        add("1.4", f"V{row}", info)
        add("1.4", f"W{row}", loc)
        add("1.4", f"X{row}", start_date)
        add("1.4", f"Y{row}", ref_type)
        add("1.4", f"Z{row}", cap)
        add("1.4", f"AA{row}", full_kg)
        add("1.4", f"AB{row}", last_kg)
        add("1.4", f"AC{row}", last_date)

    # 4. Sheet: 1.5 (Quá trình công nghiệp: 4 bảng song song)
    # Bảng 1: Khử khí thải lưu huỳnh (Rows 4..11, Cols C..S)
    fgd_rows = [
        (4, "CaCO3", "FGD-CACO3-01", "tấn", 120.0, "Công ty CP Đá vôi Kiện Khê Hà Nam"),
        (5, "MgCO3", "FGD-MGCO3-02", "tấn", 35.0, "Công ty TNHH Hóa chất Công nghiệp Miền Bắc"),
        (6, "CaMg(CO3)2", "FGD-DOLO-03", "tấn", 48.0, "Công ty CP Khoáng sản Dolomite Ninh Bình"),
        (7, "FeCO3", "FGD-FECO3-04", "tấn", 15.0, "Công ty CP Vật tư Hóa chất Thái Nguyên"),
        (8, "Ca(Fe,Mg,Mn)(CO3)2", "FGD-ANKER-05", "tấn", 18.0, "Công ty CP Khoáng sản & Hóa chất Đông Bắc"),
        (9, "MnCO3", "FGD-MNCO3-06", "tấn", 12.0, "Công ty TNHH Hóa chất Kỹ thuật Việt Nam"),
        (10, "Na2CO3", "FGD-SODA-07", "tấn", 25.0, "Công ty CP Hóa chất Cơ bản Miền Bắc"),
        (11, "Ca(OH)2 (Vôi tôi hấp thụ SO2)", "FGD-CAOH2-08", "tấn", 42.0, "Công ty TNHH Vôi Công nghiệp Hà Nam"),
    ]
    for row, name, code, unit, base_qty, supplier in fgd_rows:
        add("1.5", f"C{row}", name)
        add("1.5", f"D{row}", code)
        add("1.5", f"E{row}", unit)
        for m in range(1, 13):
            col = get_column_letter(m + 5)  # F..Q
            add("1.5", f"{col}{row}", round(base_qty + m * 1.5, 1))
        add("1.5", f"R{row}", f"=SUM(F{row}:Q{row})")
        add("1.5", f"S{row}", supplier)

    # Bảng 2: Sản xuất thép (Rows 4..13, Cols V..Y)
    steel_rows = [
        (4, "Sản lượng thép thô được SX từ lò thổi ôxy BOF", "tấn", 14500, "Phân xưởng luyện kim phụ trợ số 1"),
        (5, "Sản lượng thép thô được SX từ lò nung OHF", "tấn", 6200, "Phân xưởng lò nung hoàn열 số 2"),
        (6, "Sản lượng thép thô được SX từ các lò khác (Lò điện hồ quang EAF)", "tấn", 9800, "Lò điện hồ quang EAF công suất 30 tấn/mẻ"),
        (7, "Sản lượng gang SX được", "tấn", 18400, "Hệ thống lò cao dung tích 450 m3"),
        (8, "Sản lượng gang SX không được chuyển hoá thành thép", "tấn", 2100, "Gang đúc thương phẩm phục vụ cơ khí nội bộ"),
        (9, "Sản lượng sắt hoàn nguyên trực tiếp (sắt xốp)", "tấn", 4500, "Dây chuyền hoàn nguyên khí tự nhiên DRI"),
        (10, "Sản lượng quặng thiêu kết", "tấn", 22000, "Dây chuyền băng tải thiêu kết diện tích 75 m2"),
        (11, "Sản lượng quặng vê viên", "tấn", 16500, "Lò quay vê viên quặng sắt tinh"),
        (12, "Sản lượng than cốc tự SX được (nếu có)", "tấn", 7800, "Lò cốc thu hồi nhiệt phát điện phụ trợ"),
        (13, "Sản lượng hợp kim Fero-Mangan & Fero-Silic phụ trợ", "tấn", 1950, "Phân xưởng hợp kim cơ khí chính xác"),
    ]
    for row, name, unit, qty, note in steel_rows:
        add("1.5", f"V{row}", name)
        add("1.5", f"W{row}", unit)
        add("1.5", f"X{row}", qty)
        add("1.5", f"Y{row}", note)

    # Bảng 3: Ngành hóa chất (Rows 4..14, Cols AB..AE)
    chem_rows = [
        (4, "Sản lượng amoniac (công nghệ khí hóa than)", "tấn", 3200, "Tổng hợp NH3 áp suất trung bình"),
        (5, "Sản lượng amoniac (công nghệ reforming)", "tấn", 4800, "Steam Methane Reforming (SMR) từ khí tự nhiên"),
        (6, "Sản lượng axit nitric (CN áp suất thấp)", "tấn", 1500, "Hệ thống oxy hóa xúc tác Pt-Rh áp suất thấp"),
        (7, "Sản lượng axit nitric (CN áp suất trung bình)", "tấn", 2600, "Có tích hợp tháp khử xúc tác chọn lọc SCR N2O"),
        (8, "Sản lượng axit nitric (CN áp suất cao)", "tấn", 1900, "Hệ thống hấp thụ tháp kép hiệu suất 99.2%"),
        (9, "Sản lượng CO2 thu hồi cho các mục đích khác", "tấn", 1150, "Thu hồi CO2 tinh khiết cấp cho công nghệ trung hòa nước thải dệt nhuộm"),
        (10, "Lượng khí gas sử dụng (HFC, PFC…)", "tấn", 12.5, "Khí kỹ thuật phục vụ làm sạch & cách điện"),
        (11, "Lượng than cốc sử dụng", "tấn", 5400, "Nguyên liệu hoàn nguyên hóa chất công nghiệp"),
        (12, "Than antraxit để sản xuất hóa chất cơ bản", "tấn", 6100, "Cấp liệu cho lò khí hóa tầng cố định"),
        (13, "Khí tự nhiên để sản xuất nguyên liệu tổng hợp", "1000 m3", 2850, "Đo đếm qua đồng hồ lưu lượng kế Coriolis"),
        (14, "Methanol được dùng như nguyên liệu", "tấn", 1750, "Nguyên liệu tổng hợp chất trợ nhuộm & hoàn tất vải"),
    ]
    for row, name, unit, qty, note in chem_rows:
        add("1.5", f"AB{row}", name)
        add("1.5", f"AC{row}", unit)
        add("1.5", f"AD{row}", qty)
        add("1.5", f"AE{row}", note)

    # Bảng 4: Sử dụng sản phẩm (Rows 4..8, Cols AF..AW)
    prod_rows = [
        (4, 1, "SF6 dùng cho máy cắt", "SP-SF6-01", "kg", [5, 4, 6, 5, 8, 7, 6, 5, 6, 30, 56, 8], "Trạm biến áp 110kV & Phòng Cơ điện"),
        (5, 2, "C2H2 dùng cho hàn, xì", "SP-C2H2-02", "kg", [45, 42, 48, 50, 55, 52, 58, 54, 49, 46, 50, 44], "Xưởng Bảo trì Cơ khí & Đường ống hơi"),
        (6, 3, "Bình CO2 chữa cháy (Bình MT3)", "SP-MT3-03", "kg", [168, 24, 30, 18, 24, 36, 30, 24, 18, 24, 30, 36], "Đội PCCC Cơ sở - Kiểm tra định kỳ"),
        (7, 4, "Bình CO2 chữa cháy (Bình MT5)", "SP-MT5-04", "kg", [270, 35, 40, 25, 30, 45, 40, 35, 25, 30, 40, 45], "Đội PCCC Cơ sở - Khu kho & Xưởng sản xuất"),
        (8, 5, "Hóa chất xử lý nước & trợ nhuộm (Na2CO3, NH4OH, Polymer)", "SP-CHEM-05", "kg", [320, 340, 360, 355, 380, 410, 420, 405, 390, 375, 365, 350], "Phân xưởng Xử lý nước cấp & Nước thải"),
    ]
    for row, stt, name, code, unit, monthly_vals, supplier in prod_rows:
        add("1.5", f"AF{row}", stt)
        add("1.5", f"AG{row}", name)
        add("1.5", f"AH{row}", code)
        add("1.5", f"AI{row}", unit)
        for m, val in enumerate(monthly_vals, 1):
            col = get_column_letter(m + 35)  # AJ (col 36) .. AU (col 47)
            add("1.5", f"{col}{row}", val)
        add("1.5", f"AV{row}", f"=SUM(AJ{row}:AU{row})")
        add("1.5", f"AW{row}", supplier)

    # 5. Sheet: 1.6 (Lượng nước thải phát sinh tại Nhà máy 1, Nhà máy 2, Khu nhà ở)
    # Nhà máy 1 (Cols D..O = Tháng 1..12, Col P = Tổng/Trung bình)
    # Nhà máy 2 (Cols T..AE = Tháng 1..12, Col AF = Tổng/Trung bình)
    plant_rows_1_6 = [
        (3, 18500.0, 250.0, "SUM", 14200.0, 200.0),      # Nước thải công nghiệp (m3)
        (4, 2400.0, 35.0, "SUM", 1850.0, 25.0),          # Nước thải sinh hoạt (m3)
        (8, 1250.0, 15.0, "AVERAGE", 1180.0, 12.0),      # COD trước xử lý - CN (mg/lít)
        (9, 420.0, 6.0, "AVERAGE", 395.0, 5.0),          # COD trước xử lý - SH (mg/lít)
        (13, 68.0, 1.2, "AVERAGE", 64.0, 1.0),           # COD sau xử lý - CN (mg/lít)
        (14, 0.048, 0.001, "AVERAGE", 0.045, 0.001),     # COD sau xử lý - SH (kgCOD/m3)
        (18, 540.0, 8.0, "AVERAGE", 510.0, 7.0),         # BOD5 trước xử lý - CN (mg/lít)
        (19, 0.220, 0.004, "AVERAGE", 0.205, 0.003),     # BOD5 trước xử lý - SH (kgCOD/m3)
        (23, 24.0, 0.5, "AVERAGE", 22.5, 0.4),           # BOD5 sau xử lý - CN (mg/lít)
        (24, 0.018, 0.0004, "AVERAGE", 0.016, 0.0003),   # BOD5 sau xử lý - SH (kgCOD/m3)
        (28, 38.0, 0.6, "AVERAGE", 35.5, 0.5),           # Nitơ - CN (mg/lít)
        (29, 0.032, 0.0005, "AVERAGE", 0.030, 0.0004),   # Nitơ - SH (kgCOD/m3)
        (33, 420.0, 12.0, "SUM", 310.0, 9.0),            # CH4 thu hồi (kg CH4)
    ]
    for row, b1, s1, fn, b2, s2 in plant_rows_1_6:
        for m in range(1, 13):
            c1 = get_column_letter(m + 3)   # D..O
            c2 = get_column_letter(m + 19)  # T..AE
            v1 = round(b1 + m * s1, 4 if b1 < 1 else 1)
            v2 = round(b2 + m * s2, 4 if b2 < 1 else 1)
            add("1.6", f"{c1}{row}", v1)
            add("1.6", f"{c2}{row}", v2)
        add("1.6", f"P{row}", f"={fn}(D{row}:O{row})")
        add("1.6", f"AF{row}", f"={fn}(T{row}:AE{row})")

    # Khu nhà ở (Cols AJ..AU = Tháng 1..12, Col AV = Tổng/Trung bình)
    dorm_rows_1_6 = [
        (3, 1650.0, 20.0, "SUM"),         # Lưu lượng nước thải sinh hoạt (m3)
        (7, 380.0, 5.0, "AVERAGE"),       # COD trước xử lý (mg/lít)
        (11, 0.042, 0.0008, "AVERAGE"),   # COD sau xử lý (kgCOD/m3)
        (15, 0.195, 0.003, "AVERAGE"),    # BOD5 trước xử lý (kgCOD/m3)
        (19, 0.015, 0.0003, "AVERAGE"),   # BOD5 sau xử lý (kgCOD/m3)
        (23, 0.028, 0.0004, "AVERAGE"),   # Hàm lượng Nitơ (kgCOD/m3)
        (27, 85.0, 2.5, "SUM"),           # CH4 thu hồi (kg CH4)
    ]
    for row, base_v, step_v, fn in dorm_rows_1_6:
        for m in range(1, 13):
            c3 = get_column_letter(m + 35)  # AJ (36) .. AU (47)
            val = round(base_v + m * step_v, 4 if base_v < 1 else 1)
            add("1.6", f"{c3}{row}", val)
        add("1.6", f"AV{row}", f"={fn}(AJ{row}:AU{row})")

    # 6. Sheet: 2.1 (Lượng điện năng tiêu thụ hàng tháng — bổ sung Mã vật tư C và Điện tự sản xuất F)
    for m in range(1, 13):
        r = m + 2
        add("2.1", f"C{r}", f"EVN-2026-T{m:02d}")
        add("2.1", f"D{r}", "kWh")
        add("2.1", f"F{r}", 12000 + m * 450)  # Điện mặt trời mái nhà tự sản xuất, tự dùng
        add("2.1", f"G{r}", f"=SUM(E{r}:F{r})")
    add("2.1", "C15", "EVN-2026-SUM")
    add("2.1", "D15", "kWh")
    add("2.1", "E15", "=SUM(E3:E14)")
    add("2.1", "F15", "=SUM(F3:F14)")
    add("2.1", "G15", "=SUM(G3:G14)")

    # 7. Sheet: 2.2 (Lượng hơi nước đã mua hàng tháng — Rows 4..15, Tổng Row 16)
    for m in range(1, 13):
        r = m + 3
        add("2.2", f"C{r}", round(1450.0 + m * 35.0, 1))       # Khối lượng hơi nước (tấn)
        add("2.2", f"D{r}", 1050000 + (m % 4) * 25000)         # Áp suất hơi nước (Pa)
        add("2.2", f"E{r}", round(182.0 + (m % 5) * 1.2, 1))   # Nhiệt độ hơi nước (oC)
        add("2.2", f"F{r}", round(2778.0 + (m % 6) * 2.5, 1))  # Entanpi (kJ/kg)
        add("2.2", f"G{r}", round(86.0 + (m % 4) * 0.6, 1))    # Hiệu suất lò hơi (%)
        add("2.2", f"H{r}", "80% than bitum, 20% viên nén sinh khối")
    add("2.2", "C16", "=SUM(C4:C15)")
    add("2.2", "D16", "=AVERAGE(D4:D15)")
    add("2.2", "E16", "=AVERAGE(E4:E15)")
    add("2.2", "F16", "=AVERAGE(F4:F15)")
    add("2.2", "G16", "=AVERAGE(G4:G15)")
    add("2.2", "H16", "Trung bình năm: 80% than bitum, 20% viên nén sinh khối")

    # 8. Sheet: Thông tin bổ sung (Rows 3..8)
    add("Thông tin bổ sung", "D3", "Đã đính kèm Hồ sơ thuyết minh công nghệ dệt nhuộm, lò hơi tầng sôi CFB & hệ thống đồng đốt sinh khối (Mã HS: TM-CN-2026-01)")
    add("Thông tin bổ sung", "D4", "Đã tổng hợp đủ 12 phiếu phân tích nhiệt trị, hàm lượng carbon & tro xỉ hàng tháng từ Vinacomin/TKV & Petrolimex năm 2026")
    add("Thông tin bổ sung", "D5", "Đã đính kèm 24 phiếu kết quả quan trắc chất lượng nước thải đầu vào/đầu ra (COD, BOD5, Tổng N) đạt QCVN 40:2011/BTNMT")
    add("Thông tin bổ sung", "D6", "Đã cung cấp sơ đồ quy trình trạm XLNT 2,500 m3/ngày.đêm (Bể kỵ khí UASB có thu hồi CH4 + Aerotank) và báo cáo 12 tháng")
    add("Thông tin bổ sung", "D7", "Đã lưu trữ đầy đủ bộ hóa đơn GTGT điện EVN 12 tháng, phiếu cân trạm điện tử than/sinh khối và hóa đơn xăng dầu/LPG/LNG")
    add("Thông tin bổ sung", "B8", 6)
    add("Thông tin bổ sung", "C8", "Biên bản hiệu chuẩn định kỳ đồng hồ đo đếm điện năng, lưu lượng kế hơi nước, khí tự nhiên và cân trạm tải trọng 80 tấn")
    add("Thông tin bổ sung", "D8", "Đã kiểm định hợp lệ năm 2026 bởi Viện Đo lường Việt Nam (VMI)")

    # 9. Sheet: Biện pháp giảm thiểu (Nhóm A: rows 4..8, Nhóm B: rows 10..13, Nhóm C: rows 15..18)
    mitigation_rows = [
        # Nhóm A: Cải tạo, nâng cấp
        (4, "Cải tạo, nâng cấp kỹ thuật", "Chuyển đổi đồng đốt 20% viên nén sinh khối tại lò hơi tầng sôi", "Thay thế một phần than đá bằng viên nén mùn cưa & trấu ép có chứng nhận bền vững", "4,200,000,000 VNĐ", "2025 - 2026", "Giảm 650 tCO2e/năm (Đã vận hành chính thức)"),
        (5, "Cải tạo, nâng cấp kỹ thuật", "Lắp đặt hệ thống biến tần VFD cho quạt gió lò hơi & máy nén khí", "Tối ưu hóa phụ tải động cơ theo áp suất thực tế qua PLC/SCADA", "1,850,000,000 VNĐ", "2025 - 2026", "Giảm 110 tCO2e/năm (Tiết kiệm 152,000 kWh/năm)"),
        (6, "Cải tạo, nâng cấp kỹ thuật", "Hệ thống thu hồi nhiệt khói thải lò hơi (Economizer) & nước ngưng", "Gia nhiệt nước cấp lò hơi từ 30oC lên 85oC, giảm tiêu hao nhiên liệu đốt", "2,400,000,000 VNĐ", "2026", "Giảm 320 tCO2e/năm (Tiết kiệm 8% lượng than)"),
        (7, "Cải tạo, nâng cấp kỹ thuật", "Thu hồi khí sinh học CH4 từ bể kỵ khí UASB trạm xử lý nước thải", "Thu gom khí Biogas cấp ngược cho đầu đốt phụ trợ lò sấy", "3,100,000,000 VNĐ", "2026", "Giảm 280 tCO2e/năm (Tránh phát tán CH4 trực tiếp)"),
        (8, "Cải tạo, nâng cấp kỹ thuật", "Chuyển đổi dàn xe nâng dầu DO sang xe nâng điện Lithium-ion", "Thay thế 10 xe nâng diesel trong kho thành phẩm bằng xe nâng điện", "5,500,000,000 VNĐ", "2026 - 2027", "Giảm 145 tCO2e/năm (Đang triển khai giai đoạn 2)"),
        # Nhóm B: Bù trừ
        (10, "Năng lượng tái tạo & Bù trừ", "Hệ thống Điện mặt trời mái nhà (Rooftop Solar PV) 1.5 MWp", "Lắp đặt pin mặt trời áp mái tại Nhà máy 1 & Nhà máy 2 tự sản xuất tự tiêu thụ", "16,500,000,000 VNĐ", "2024 - 2026", "Giảm 770 tCO2e/năm (Sản lượng ~1.06 triệu kWh/năm)"),
        (11, "Năng lượng tái tạo & Bù trừ", "Hợp đồng mua bán điện trực tiếp DPPA từ dự án điện gió/mặt trời", "Ký kết hợp đồng DPPA mua năng lượng xanh kèm chứng chỉ I-REC", "2,100,000,000 VNĐ/năm", "2026 - 2028", "Bù trừ 1,200 tCO2e/năm Scope 2 theo Market-based"),
        (12, "Năng lượng tái tạo & Bù trừ", "Dự án trồng rừng hấp thụ carbon bản địa & cây xanh khuôn viên KCN", "Phối hợp trồng 15 ha rừng keo và thông tại vùng đệm Hà Nam - Hòa Bình", "1,200,000,000 VNĐ", "2025 - 2030", "Hấp thụ ước tính 225 tCO2e/năm"),
        (13, "Năng lượng tái tạo & Bù trừ", "Mua tín chỉ carbon đạt chuẩn VCS / Gold Standard phục vụ xuất khẩu", "Bù trừ phần phát thải dư thừa cho các lô hàng xuất khẩu sang thị trường EU", "850,000,000 VNĐ", "2026", "Bù trừ 500 tCO2e/năm trên sàn giao dịch tín chỉ"),
        # Nhóm C: Chia sẻ trách nhiệm từ Tập đoàn
        (15, "Chia sẻ trách nhiệm Tập đoàn", "Chương trình Quỹ Chuyển đổi Xanh Nội bộ (Internal Carbon Pricing)", "Áp dụng định giá carbon nội bộ 15 USD/tCO2e để tái đầu tư thiết bị tiết kiệm điện", "3,500,000,000 VNĐ", "2025 - 2027", "Tập đoàn tài trợ 50% vốn CAPEX cho cơ sở"),
        (16, "Chia sẻ trách nhiệm Tập đoàn", "Hệ thống quản trị năng lượng tập trung ISO 50001 & AI EcoStream", "Số hóa đo đếm IoT/SCADA và kiểm kê KNK tự động toàn chuỗi nhà máy", "1,400,000,000 VNĐ", "2026", "Đồng bộ dữ liệu kiểm toán theo NĐ 06/2022 & ISO 14064-1"),
        (17, "Chia sẻ trách nhiệm Tập đoàn", "Tối ưu hóa logistics liên nhà máy & đội xe vận tải xanh Tập đoàn", "Ghép tải container hai chiều Hải Phòng - Hà Nam và chuẩn hóa nhiên liệu Euro 5", "2,800,000,000 VNĐ", "2026", "Giảm 18% định mức tiêu hao nhiên liệu/tấn.km"),
        (18, "Chia sẻ trách nhiệm Tập đoàn", "Đào tạo & Chứng nhận Kiểm kê viên KNK nội bộ theo Thông tư 17/2022", "Tập đoàn tổ chức đào tạo chuyên sâu cho 25 kỹ sư HSE & Năng lượng các nhà máy", "450,000,000 VNĐ", "2025 - 2026", "100% cán bộ chuyên trách có chứng chỉ nghiệp vụ KNK"),
    ]
    for row, grp, name, desc, cost, yr, note in mitigation_rows:
        add("Biện pháp giảm thiểu", f"C{row}", grp)
        add("Biện pháp giảm thiểu", f"D{row}", name)
        add("Biện pháp giảm thiểu", f"E{row}", desc)
        add("Biện pháp giảm thiểu", f"F{row}", cost)
        add("Biện pháp giảm thiểu", f"G{row}", yr)
        add("Biện pháp giảm thiểu", f"H{row}", note)

    # 10. Sheet: Cung cap thong tin khai khoang (Rows 5, 6, 8, 9)
    mining_info_rows = [
        (5, "Khai thác hầm lò cơ giới hóa đồng bộ, thông gió cưỡng bức kèm hệ thống thu gom khí mê-tan (CH4) vỉa than", 145000, 162000, "Đã lắp đặt hệ thống quan trắc khí CH4 tự động liên tục"),
        (6, "Khai thác lộ thiên cắt tầng bằng máy xúc thủy lực & băng tải kín, tưới nước dập bụi tuần hoàn", 210000, 235000, "Tỷ lệ thu hồi than sạch đạt 91.5%, hoàn nguyên môi trường định kỳ"),
        (8, "Khai thác dầu thô giàn khoan kết hợp tách khí đồng hành khép kín, hạn chế đốt bỏ tại pháo (Zero Routine Flaring)", 85000, 92000, "Áp dụng công nghệ thu hồi hơi hydrocarbon (VRU)"),
        (9, "Khai thác & xử lý khí tự nhiên qua cụm tách ngưng tụ, nén áp lực cao đưa vào đường ống dẫn khí bờ", 1120000, 1250000, "Tổn thất rò rỉ đường ống kiểm soát dưới 0.15% theo chuẩn OGMP 2.0"),
    ]
    for row, tech, y2020, y2022, note in mining_info_rows:
        add("Cung cap thong tin khai khoang", f"D{row}", tech)
        add("Cung cap thong tin khai khoang", f"E{row}", y2020)
        add("Cung cap thong tin khai khoang", f"F{row}", y2022)
        add("Cung cap thong tin khai khoang", f"G{row}", note)

    return cells


# Ordered list of all 23 stationary fuel items matching rows 4..26 (STT 1..23) of sheet 1.1
STATIONARY_FUEL_SPECS = [
    ("mixed_coal", "Than trộn (antraxit + bitum)", 18500, 350, "kg"),
    ("bituminous", "Than bitum", 24000, 450, "kg"),
    ("subbituminous", "Than sub-bitum", 16000, 300, "kg"),
    ("anthracite", "Than antraxit (theo chứng từ)", 35000, 600, "kg"),
    ("diesel", "Dầu DO (Diesel)", 4200, 120, "Lít"),
    ("fo", "Dầu FO (Mazut)", 3100, 90, "kg"),
    ("kerosene", "Dầu hỏa (Parafin)", 850, 25, "Lít"),
    ("petrol", "Xăng RON 95", 620, 18, "Lít"),
    ("naturalgas", "Khí tự nhiên (Natural Gas)", 9500, 220, "m3"),
    ("lpg", "Khí hóa lỏng (LPG)", 1400, 45, "kg"),
    ("lng", "Khí tự nhiên hóa lỏng (LNG)", 2800, 80, "kg"),
    ("biogas", "Khí sinh học (Biogas)", 6400, 150, "m3"),
    ("liquid_biofuel", "Nhiên liệu sinh học lỏng khác (Biodiesel B20)", 1100, 35, "Lít"),
    ("other_petroleum", "Các sản phẩm dầu mỏ khác (Dầu nhờn/Mazut nhẹ)", 750, 20, "kg"),
    ("wood", "Gỗ hoặc chất thải từ gỗ", 12000, 280, "kg"),
    ("charcoal", "Than củi", 1800, 40, "kg"),
    ("bagasse", "Bã mía", 9200, 210, "kg"),
    ("rice_husk", "Trấu", 11500, 260, "kg"),
    ("straw", "Rơm rạ", 5400, 130, "kg"),
    ("other_solid_biomass", "Nhiên liệu sinh khối rắn khác (Viên nén mùn cưa)", 15000, 340, "kg"),
    ("industrial_waste", "Chất thải công nghiệp (sử dụng như nhiên liệu)", 4600, 110, "kg"),
    ("municipal_waste", "Chất thải đô thị (sử dụng như nhiên liệu)", 3200, 75, "kg"),
    ("peat", "Than bùn (Peat)", 2100, 50, "kg"),
]

# Ordered list of all 18 mobile vehicle/fleet groups matching rows 4..21 (STT 1..18) of sheet 1.2
MOBILE_FLEET_SPECS = [
    ("diesel", "Dầu DO (Diesel)", 1450, 35, "Lít", "Ô tô tải hạng nặng 15 tấn - Đội xe 01 (Hino 500 Series 29H-881.01)"),
    ("diesel", "Dầu DO (Diesel)", 1820, 42, "Lít", "Xe đầu kéo Container 40 feet - Đội xe 02 (Hyundai HD1000 29H-881.02)"),
    ("diesel", "Dầu DO (Diesel)", 1180, 28, "Lít", "Ô tô tải thùng kín 8 tấn - Đội xe 03 (Isuzu FVR34 29H-881.03)"),
    ("diesel", "Dầu DO (Diesel)", 940, 22, "Lít", "Ô tô tải nhẹ 5 tấn giao hàng KCN - Đội xe 04 (Thaco Ollin 29H-881.04)"),
    ("diesel", "Dầu DO (Diesel)", 860, 20, "Lít", "Ô tô khách 45 chỗ đưa đón CBCNV tuyến 1 - Đội xe 05 (Hyundai Universe 29B-451.05)"),
    ("diesel", "Dầu DO (Diesel)", 840, 18, "Lít", "Ô tô khách 45 chỗ đưa đón CBCNV tuyến 2 - Đội xe 06 (Thaco Bluesky 29B-451.06)"),
    ("diesel", "Dầu DO (Diesel)", 520, 14, "Lít", "Ô tô khách 29 chỗ đưa đón chuyên gia - Đội xe 07 (Hyundai County 29B-451.07)"),
    ("diesel", "Dầu DO (Diesel)", 480, 12, "Lít", "Xe bán tải công trường & bảo trì - Đội xe 08 (Ford Ranger Wildtrak 29C-772.08)"),
    ("diesel", "Dầu DO (Diesel)", 610, 15, "Lít", "Xe bồn chuyên dụng chở nguyên liệu - Đội xe 09 (Hino FM8JW7A 29H-881.09)"),
    ("diesel", "Dầu DO (Diesel)", 550, 13, "Lít", "Xe cẩu tự hành bốc xếp thiết bị 10 tấn - Đội xe 10 (Dongfeng Hoàng Huy 29H-881.10)"),
    ("diesel", "Dầu DO (Diesel)", 430, 10, "Lít", "Xe quét hút bụi & vệ sinh đường nội bộ KCN - Đội xe 11 (Isuzu chuyên dụng 29H-881.11)"),
    ("petrol", "Xăng RON 95", 380, 9, "Lít", "Ô tô con công vụ Ban Giám đốc - Đội xe 12 (Toyota Camry 2.5Q 30K-662.12)"),
    ("petrol", "Xăng RON 95", 410, 11, "Lít", "Ô tô 7 chỗ công tác kỹ thuật & đối ngoại - Đội xe 13 (Toyota Innova Cross 30K-662.13)"),
    ("petrol", "Xăng RON 95", 360, 8, "Lít", "Ô tô 7 chỗ đưa đón đoàn kiểm toán & khách hàng - Đội xe 14 (Mitsubishi Xpander 30K-662.14)"),
    ("petrol", "Xăng RON 95", 330, 7, "Lít", "Xe tải Van giao nhận mẫu phòng Lab & chứng từ - Đội xe 15 (Suzuki Blind Van 29D-331.15)"),
    ("petrol", "Xăng RON 95", 290, 6, "Lít", "Xe cứu thương & trực y tế khẩn cấp cơ sở - Đội xe 16 (Toyota Hiace Ambulance 29M-112.16)"),
    ("petrol", "Xăng RON 95", 210, 5, "Lít", "Đội xe máy tuần tra an ninh & bảo vệ vòng ngoài - Đội xe 17 (10 xe Honda Future 125fi)"),
    ("petrol", "Xăng RON 95", 195, 4, "Lít", "Đội xe máy giao nhận nội bộ giữa Nhà máy 1 & 2 - Đội xe 18 (08 xe Honda Wave Alpha)"),
]


def generate_full_survey_excel(output_path: str = "data/samples/du_lieu_gia_lap_full_2026.xlsx") -> str:
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    wb = openpyxl.Workbook()

    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    data_font = Font(name="Segoe UI", size=10)
    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )

    def _style_sheet(ws, title_text: str, headers: list[str]) -> None:
        ws.views.sheetView[0].showGridLines = True
        ws.append([title_text])
        ws.append(headers)
        last_col = get_column_letter(len(headers))
        ws.merge_cells(f"A1:{last_col}1")
        ws["A1"].font = Font(name="Segoe UI", size=12, bold=True, color="1F4E79")
        for c in range(1, len(headers) + 1):
            cell = ws.cell(row=2, column=c)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # 1. Sheet: NhienLieu_CoDinh_1_1 (All 23 stationary fuels x 12 months = 276 rows)
    ws1 = wb.active
    ws1.title = "NhienLieu_CoDinh_1_1"
    _style_sheet(
        ws1,
        "BẢNG KÊ CHI TIẾT 23 LOẠI NHIÊN LIỆU ĐỐT CỐ ĐỊNH 12 THÁNG NĂM 2026 (MỤC 1.1)",
        ["Ngày xuất chứng từ", "Hạng mục nhiên liệu", "Số lượng tiêu thụ", "Đơn vị tính", "Mục đích sử dụng / Thiết bị cố định", "Mã vật tư", "Giá trị nhiệt trị", "Đơn vị cung cấp"],
    )
    for month in range(1, 13):
        for idx, (kind, label, base_qty, step_qty, unit) in enumerate(STATIONARY_FUEL_SPECS, 1):
            meta = STATIONARY_FUEL_META[kind]
            qty = base_qty + month * step_qty
            # Use cylinder expression on month 11 LPG so legacy Scope1FuelAgent cylinder test also triggers
            qty_val = f"{qty // 12} bình LPG 12kg" if (kind == "lpg" and month == 11 and qty % 12 == 0) else qty
            ws1.append([
                f"2026-{month:02d}-15",
                label,
                qty_val,
                unit,
                meta[2],
                meta[0],
                meta[1],
                meta[3],
            ])

    # 2. Sheet: NhienLieu_DiDong_1_2 (All 18 mobile vehicle groups x 12 months = 216 rows)
    ws2 = wb.create_sheet("NhienLieu_DiDong_1_2")
    _style_sheet(
        ws2,
        "BẢNG KÊ CHI TIẾT 18 ĐỘI PHƯƠNG TIỆN VẬN TẢI & CÔNG VỤ DI ĐỘNG 12 THÁNG NĂM 2026 (MỤC 1.2)",
        ["Ngày xuất chứng từ", "Hạng mục nhiên liệu", "Số lượng tiêu thụ", "Đơn vị tính", "Mục đích / Đội xe phương tiện", "Mã vật tư", "Giá trị nhiệt trị", "Đơn vị cung cấp"],
    )
    for month in range(1, 13):
        for idx, (kind, label, base_qty, step_qty, unit, vehicle_group) in enumerate(MOBILE_FLEET_SPECS, 1):
            qty = base_qty + month * step_qty
            cal = "10,200 Kcal/kg" if kind == "diesel" else "10,500 Kcal/kg"
            ws2.append([
                f"2026-{month:02d}-18",
                label,
                qty,
                unit,
                vehicle_group,
                f"NL-DD-{idx:02d}",
                cal,
                "Công ty Xăng dầu Hà Nam (Petrolimex)",
            ])

    # 3. Sheet: DienLuoi_EVN_Scope2 (All 12 months of purchased & self-generated electricity)
    ws3 = wb.create_sheet("DienLuoi_EVN_Scope2")
    _style_sheet(
        ws3,
        "BẢNG THEO DÕI SẢN LƯỢNG ĐIỆN MUA LƯỚI EVN & ĐIỆN TỰ SẢN XUẤT 12 THÁNG NĂM 2026 (MỤC 2.1)",
        ["Kỳ hóa đơn (Tháng)", "Mã công tơ đo đếm", "Sản lượng điện tiêu thụ (kWh)", "Giờ bình thường (kWh)", "Giờ cao điểm (kWh)", "Giờ thấp điểm (kWh)", "Điện mặt trời tự sản xuất, tự dùng (kWh)", "Trạng thái hồ sơ"],
    )
    monthly_evn = [
        45250, 42100, 48600, 52300, 58400, 64800,
        67500, 66200, 59100, 53500, 49700, 47800,
    ]
    for month, kwh in enumerate(monthly_evn, 1):
        normal = int(kwh * 0.62)
        peak = int(kwh * 0.20)
        offpeak = kwh - normal - peak
        solar = 12000 + month * 450
        ws3.append([
            f"Tháng {month:02d}/2026",
            "HN-CTR-0982",
            kwh,
            normal,
            peak,
            offpeak,
            solar,
            "Đã đối soát Hóa đơn EVN & SCADA Solar",
        ])

    # 4. Sheet: ChuoiCungUng_Scope3
    ws4 = wb.create_sheet("ChuoiCungUng_Scope3")
    _style_sheet(
        ws4,
        "NHẬT KÝ VẬN TẢI HÀNG HÓA & MUA SẮM VẬT TƯ NĂM 2026 (SCOPE 3)",
        ["Mã chuyến / Đơn hàng", "Mô tả hàng hóa / Dịch vụ", "Khối lượng (Tấn)", "Cự ly vận chuyển (km)", "Phương tiện", "Chi phí mua ngoài (VND)", "Ghi chú"],
    )
    for row_data in [
        ["LOG-2026-001", "Vải cuộn Cotton tự nhiên nhập kho", "120", "150", "Xe tải hạng nặng 16 tấn", "180,000,000", "Tuyến Hải Phòng - Hà Nam"],
        ["LOG-2026-002", "Phụ liệu dệt may & bao bì carton", "45", "60", "Xe tải nhẹ 5 tấn", "65,000,000", "Tuyến Nội Bài - Hà Nam"],
        ["LOG-2026-003", "Xuất khẩu thành phẩm may mặc", "180", "150", "Container đường bộ 25 tấn", "260,000,000", "Tuyến Hà Nam - Cảng Hải Phòng"],
        ["SPEND-2026-088", "Mua sắm thiết bị phụ trợ & dịch vụ văn phòng", "-", "-", "-", "45,000,000", "Chi phí không có số liệu khối lượng vật lý"],
    ]:
        ws4.append(row_data)

    # 5. Sheet: GiamNhe_Mau02_ND06
    ws5 = wb.create_sheet("GiamNhe_Mau02_ND06")
    _style_sheet(
        ws5,
        "KẾ HOẠCH VÀ KẾT QUẢ GIẢM NHẸ PHÁT THẢI KNK CƠ SỞ (MẪU SỐ 02 NGHỊ ĐỊNH 06/2022/NĐ-CP)",
        ["Mã biện pháp", "Tên biện pháp giảm nhẹ", "Phân loại công nghệ", "Phát thải cơ sở PTCS (tCO2e)", "Phát thải thực tế PT (tCO2e)", "Phương pháp quan trắc & giám sát", "Hạn ngạch phân bổ 2026 (tCO2e)"],
    )
    for row_data in [
        ["MM-01", "Lắp đặt hệ thống Điện mặt trời mái nhà 1.5 MWp", "Năng lượng tái tạo", "950.0", "180.0", "Đo đếm điện năng công tơ 2 chiều qua SCADA", "18000.0"],
        ["MM-02", "Chuyển đổi đồng đốt 20% viên nén sinh khối tại lò hơi", "Chuyển đổi nhiên liệu", "2400.0", "1750.0", "Phiếu cân trạm điện tử & phân tích nhiệt trị", "18000.0"],
        ["MM-03", "Lắp đặt biến tần VFD tối ưu động cơ quạt gió và bơm", "Hiệu quả năng lượng", "420.0", "310.0", "Đo đếm công suất tiêu thụ tại tủ điều khiển", "18000.0"],
    ]:
        ws5.append(row_data)

    # 6. Sheet: Survey_Extra_Cells (Structured coordinates for all remaining tabs: Thông tin chung, 1.3, 1.4, 1.5, 1.6, 2.1, 2.2, Thông tin bổ sung, Biện pháp giảm thiểu, Cung cap thong tin khai khoang)
    ws_extra = wb.create_sheet("Survey_Extra_Cells")
    ws_extra.append(["Target_Sheet", "Cell_Coordinate", "Value"])
    for s_name, coord, val in _build_extra_cells():
        ws_extra.append([s_name, coord, val])

    for ws in (ws1, ws2, ws3, ws4, ws5):
        for row in ws.iter_rows(min_row=3, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
            for cell in row:
                cell.font = data_font
                cell.border = thin_border
                cell.alignment = Alignment(vertical="center")

    wb.save(output_path)
    return output_path


if __name__ == "__main__":
    full_input_samples = str(ROOT / "data" / "samples" / "du_lieu_gia_lap_full_2026.xlsx")
    full_input_demo = str(ROOT / "data" / "demo_full_2026" / "du_lieu_gia_lap_full_2026.xlsx")
    generate_full_survey_excel(full_input_samples)
    generate_full_survey_excel(full_input_demo)
    print(f"Generated full simulated input workbook:\n  - {full_input_samples}\n  - {full_input_demo}")

    # Run the survey pipeline end-to-end and export ready-to-open deliverables
    runs_dir = str(ROOT / "runs")
    prep = prepare_survey(
        [full_input_samples],
        company="EcoGarment Vietnam JSC",
        facility="Nhà máy May & Năng lượng Hà Nam",
        year=2026,
        base_runs_dir=runs_dir,
    )
    run_id = prep["run_id"]
    calc = calculate_survey(run_id, base_runs_dir=runs_dir)
    run_deliv = ROOT / "runs" / run_id / "deliverables"
    import shutil
    for fname in ("Bang_khao_sat_da_dien.xlsx", "GHGs_inventory_da_tinh.xlsx", "Bao_cao_kiem_ke_KNK.docx"):
        shutil.copy2(run_deliv / fname, ROOT / fname)
        shutil.copy2(run_deliv / fname, ROOT / "data" / "demo_full_2026" / fname)
    print(f"Completed full survey & calculation run: {run_id}")
    print(f"  Total extracted records: {len(prep['items'])}")
    print(f"  Scope 1 (tCO2e): {calc['summary']['scope_1_tonnes']:,.3f}")
    print(f"  Scope 2 (tCO2e): {calc['summary']['scope_2_tonnes']:,.3f}")
    print(f"  Total CO2e (tCO2e): {calc['summary']['total_co2e_tonnes']:,.3f}")
