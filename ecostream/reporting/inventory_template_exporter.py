"""Produce an inventory in the supplied workbook format without retaining example activities.

The workbook contains a different calculation methodology (TJ, gas-specific EF) than
EcoStream's kg CO2e/unit factors. Keep its formulas for inspection, while showing
verified Python calculation results separately rather than asserting equality.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.workbook.properties import CalcProperties

from ecostream.ingestion.survey_workbook import FUEL_ROWS, TEMPLATES, SurveyData, SurveyValidationError
from ecostream.models.results import AuditReport

INVENTORY_NAME = "_GHGs-inventory.xlsx"


def _clear_example_inputs(book) -> None:
    for name in ("S1-Stationary Combustion", "S1-Mobile Combustion"):
        sheet = book[name]
        for row in range(9, 67):
            for col in range(4, 16):  # D:O activity quantities only
                cell = sheet.cell(row, col)
                if not isinstance(cell, MergedCell) and cell.data_type != "f" and isinstance(cell.value, (int, float)):
                    cell.value = None
            # Template holds pre-entered units and conversion formulas, but no other activity cells.
            if not isinstance(sheet[f"C{row}"], MergedCell):
                sheet[f"C{row}"] = None
            for col in (16, 17, 19, 21, 23, 25, 26):
                cell = sheet.cell(row, col)
                if not isinstance(cell, MergedCell) and cell.data_type != "f" and isinstance(cell.value, (int, float)):
                    cell.value = None
    for name, start, end, c0, c1 in (
        ("S1-Refrigerants", 7, 9, 5, 16),
        ("S1-Industrial processes", 7, 17, 4, 15),
        ("S1-Wastewater Treatment", 9, 25, 4, 15),
        ("S2-Electricity Consumption", 7, 18, 3, 5),
    ):
        sheet = book[name]
        for row in range(start, end + 1):
            for col in range(c0, c1 + 1):
                cell = sheet.cell(row, col)
                if not isinstance(cell, MergedCell) and cell.data_type != "f" and isinstance(cell.value, (int, float)):
                    cell.value = None


def export_inventory(data: SurveyData, report: AuditReport, target: str) -> list[str]:
    book = load_workbook(TEMPLATES / INVENTORY_NAME)
    if "S2-Electricity Consumption" not in book or "Summary_detail" not in book:
        raise SurveyValidationError("Workbook kiểm kê không đúng mẫu")
    _clear_example_inputs(book)
    grouped = defaultdict(float)
    for item in data.items:
        if item.kind == "electricity":
            grouped[("S2-Electricity Consumption", item.month + 6, "kWh", item.month)] += item.quantity
            continue
        _, row, standard = FUEL_ROWS[item.kind]
        if item.unit != standard:
            raise SurveyValidationError(f"{item.sheet}!{item.coordinate}: đơn vị sai khi chuyển sang workbook kiểm kê")
        sheet = "S1-Mobile Combustion" if item.sheet == "1.2" else "S1-Stationary Combustion"
        if item.sheet == "1.2" and item.kind not in ("diesel", "petrol"):
            raise SurveyValidationError(f"{item.sheet}!{item.coordinate}: mẫu kiểm kê chưa có hệ số khí cho nhiên liệu di động {item.kind}")
        grouped[(sheet, row, item.unit, item.month)] += item.quantity
    warnings = []
    template_fuel_total = 0.0
    template_electricity_total = 0.0
    from ecostream.factors.database import get_factor_database
    grid = get_factor_database().get("EF-SCOPE2-VN-GRID")
    for (name, row, unit, month), quantity in grouped.items():
        sheet = book[name]
        if name.startswith("S1-"):
            # The provided workbook's default Q formula for stationary diesel assumes tonnes;
            # map litres via the density provided by its Conversion Factors sheet.
            if unit == "liter":
                if row not in (12, 18):
                    raise SurveyValidationError(f"{name}!B{row}: chưa có tỷ trọng quy đổi cho nhiên liệu này")
                density = "$F$5" if row == 18 else "$F$7"
                sheet[f"Q{row}"] = f"=P{row}*'Conversion Factors'!{density}/1000000"
                warnings.append(f"{name}!Q{row}: quy đổi lít sang ktonnes theo tỷ trọng workbook gốc; cần xác nhận tỷ trọng")
            elif unit == "kg":
                sheet[f"Q{row}"] = f"=P{row}/1000000"
            elif unit == "m3":
                sheet[f"Q{row}"] = f"=P{row}*'Conversion Factors'!$F$9/1000000"
            sheet[f"C{row}"] = {"liter": "Litres", "kg": "kg", "m3": "m3"}[unit]
            sheet[f"P{row}"] = f"=SUM(D{row}:O{row})"
            if not isinstance(sheet[f"R{row}"].value, (int, float)) or not isinstance(sheet[f"T{row}"].value, (int, float)):
                raise SurveyValidationError(f"{name}!R{row}/T{row}: thiếu hệ số nhiệt trị hoặc CO2 của mẫu")
            sheet[f"S{row}"] = f'=IF(Q{row}=0,"",Q{row}*R{row})'
            for factor_col, output_col in (("T", "U"), ("V", "W"), ("X", "Y")):
                if sheet[f"{factor_col}{row}"].value is not None:
                    sheet[f"{output_col}{row}"] = f'=IF(Q{row}=0,"",S{row}*{factor_col}{row}/1000)'
            sheet[f"Z{row}"] = f"=U{row}+W{row}*28+Y{row}*273"
            sheet.cell(row, month + 3).value = quantity
            density = book["Conversion Factors"]["F5" if row == 18 else "F7"].value if unit == "liter" else 1.0
            if unit == "m3":
                density = book["Conversion Factors"]["F9"].value
            q_kilotonnes = quantity * density / 1_000_000
            energy_tj = q_kilotonnes * sheet[f"R{row}"].value
            template_fuel_total += energy_tj * (sheet[f"T{row}"].value + 28 * sheet[f"V{row}"].value + 273 * sheet[f"X{row}"].value) / 1000
        else:
            template_electricity_total += quantity * grid.factor_value / 1000
            sheet[f"C{row}"] = quantity
            sheet[f"D{row}"] = 0.001
            # Factor is kept in the same unit as template: tCO2/MWh.
            sheet[f"E{row}"] = grid.factor_value
            sheet[f"F{row}"] = f"=C{row}*D{row}*E{row}"
    book["S2-Electricity Consumption"]["E4"] = f"Grid emissions factor {grid.year} ({grid.source})"
    year = report.summary.reporting_period
    book["S2-Electricity Consumption"]["C4"] = f"Amount of electricity purchased from the national grid in {year}"
    book["S1-Industrial processes"]["B3"] = f"AD from industrial processes {year}"
    for row in (4, 16):
        book["S1-Wastewater Treatment"][f"B{row}"] = year
    for row in (5, 17):
        book["S1-Wastewater Treatment"][f"P{row}"] = f"Amount of wastewater generated {year}"
    book["S2-Electricity Consumption"]["C19"] = "=SUM(C7:C18)"
    book["S2-Electricity Consumption"]["F19"] = "=SUM(F7:F18)"
    book.calculation = CalcProperties(calcMode="auto", fullCalcOnLoad=True, forceFullCalc=True)
    # A clear reconciliation sheet prevents treating stale Excel cached results as verified.
    if "EcoStream đối soát" in book:
        del book["EcoStream đối soát"]
    audit = book.create_sheet("EcoStream đối soát")
    audit.append(["BẢN KIỂM KÊ GIỚI HẠN SCOPE 1/2 — CẦN RÀ SOÁT TRƯỚC KHI NỘP"])
    audit.append(["Doanh nghiệp", report.summary.company_name])
    audit.append(["Cơ sở", report.summary.facility_location])
    audit.append(["Năm", report.summary.reporting_period])
    audit.append(["Nguồn dữ liệu", "Biểu khảo sát đã kiểm tra; không dùng số liệu ví dụ trong template"])
    audit.append(["Phương pháp EcoStream", "Số lượng × hệ số phát thải (kgCO2e/đơn vị) / 1000"])
    audit.append(["Lưu ý", "Các sheet gốc dùng hệ số khí/TJ và công thức riêng, CHƯA đối soát với kết quả EcoStream; Excel cần mở bằng phần mềm hỗ trợ tính lại"])
    audit.append(["Hệ số điện", f"{grid.factor_value} kgCO2e/kWh ({grid.year}), nguồn: {grid.source}; không dùng hệ số mẫu 0.6592"])
    audit.append(["Năm hệ số", f"{grid.year}; cần xác nhận phù hợp với năm kiểm kê {report.summary.reporting_period}"])
    audit.append(["Giới hạn", "Chưa tính môi chất lạnh, công nghiệp, nước thải, hơi nước và Scope 3"])
    audit.append(["Bằng chứng", "Xem từng dòng trong biểu khảo sát và danh sách chứng từ tại phiên chạy; người dùng phải đối chiếu trước khi nộp"])
    audit.append(["Scope 1 (tCO2e)", report.summary.scope_1_tonnes])
    audit.append(["Scope 2 (tCO2e)", report.summary.scope_2_tonnes])
    audit.append(["Tổng EcoStream (tCO2e)", report.summary.total_co2e_tonnes])
    audit.append(["Scope 1 ước tính theo hệ số TJ trong mẫu (tCO2e)", template_fuel_total])
    audit.append(["Scope 2 ước tính theo công thức mẫu (tCO2e)", template_electricity_total])
    audit.append(["Chênh lệch Scope 1: mẫu trừ EcoStream (tCO2e)", template_fuel_total - report.summary.scope_1_tonnes])
    audit.append(["Chênh lệch Scope 2: mẫu trừ EcoStream (tCO2e)", template_electricity_total - report.summary.scope_2_tonnes])
    if abs(template_fuel_total - report.summary.scope_1_tonnes) > 0.01:
        warnings.append(f"Kết quả Scope 1 theo hệ số TJ của mẫu lệch {template_fuel_total - report.summary.scope_1_tonnes:+.3f} tCO2e so với EcoStream; cần xác định phương pháp chính thức")
    if abs(template_electricity_total - report.summary.scope_2_tonnes) > 0.01:
        warnings.append(f"Kết quả Scope 2 theo mẫu lệch {template_electricity_total - report.summary.scope_2_tonnes:+.3f} tCO2e; cần rà soát")
    audit.append([])
    audit.append(["Dòng", "Nguồn", "Scope", "Số lượng", "Đơn vị", "EF kgCO2e/đơn vị", "Phát thải tCO2e", "Bằng chứng"])
    for calc in report.calculations:
        audit.append([calc.activity_id, calc.description, calc.scope.value, calc.activity_value, calc.activity_unit, calc.emission_factor_value, calc.co2e_tonnes, calc.evidence.page_or_line])
    audit.column_dimensions["B"].width = 48
    audit.column_dimensions["H"].width = 40
    book.save(target)
    return warnings
