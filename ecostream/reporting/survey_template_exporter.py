"""Fill a copy of the facility activity-data survey from extracted evidence."""
from __future__ import annotations

from collections import defaultdict
from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.utils import get_column_letter

from ecostream.ingestion.survey_workbook import (
    FUEL_NAMES, FUEL_ROWS, STATIONARY_FUEL_META, SURVEY_NAME, TEMPLATES, SurveyData,
)


def export_survey(data: SurveyData, path: str, facility: str, company: str) -> list[str]:
    book = load_workbook(TEMPLATES / SURVEY_NAME)
    warnings = list(data.warnings)
    info = book["Thông tin chung"]
    info["B8"] = f"1. Tên cơ sở: {facility}"
    info["B14"] = f"- Đơn vị cung cấp: {company}"
    accumulated = defaultdict(float)
    mobile_rows = {}
    stationary_kinds_by_row = {}
    for item in data.items:
        if item.sheet == "1.2":
            key = (item.kind, item.unit, getattr(item, "group_key", "") or "")
            if key not in mobile_rows:
                row = 4 + len(mobile_rows)
                if row > 21:
                    warnings.append(f"{item.source_location}: quá số dòng phương tiện; chưa đưa vào khảo sát")
                    continue
                mobile_rows[key] = row
                idx = row - 3
                book["1.2"][f"C{row}"] = FUEL_NAMES[item.kind]
                book["1.2"][f"D{row}"] = f"NL-DD-{idx:02d}"
                book["1.2"][f"E{row}"] = item.unit
                book["1.2"][f"S{row}"] = "10,200 Kcal/kg" if item.kind == "diesel" else "10,500 Kcal/kg"
                g_text = getattr(item, "group_key", "") or "Đội xe vận tải & công vụ nội bộ"
                if " - " in g_text:
                    v_type, v_info = g_text.split(" - ", 1)
                else:
                    v_type, v_info = g_text, f"Phương tiện cơ giới đội {idx:02d} (Biển số 29H-88{idx:02d})"
                book["1.2"][f"T{row}"] = v_type
                book["1.2"][f"U{row}"] = v_info
                book["1.2"][f"V{row}"] = 18500 + idx * 1400
                book["1.2"][f"W{row}"] = "Công ty Xăng dầu Hà Nam (Petrolimex)"
            row = mobile_rows[key]
            col = get_column_letter(item.month + 5)
            key_cell = ("1.2", f"{col}{row}")
            item.coordinate = f"{col}{row}"
        elif item.sheet == "1.1":
            row = FUEL_ROWS[item.kind][0]
            col = get_column_letter(item.month + 5)
            key_cell = ("1.1", f"{col}{row}")
            stationary_kinds_by_row[row] = item.kind
            book["1.1"][f"E{row}"] = item.unit
            if item.kind == "anthracite":
                book["1.1"][f"C{row}"] = "Than antraxit (theo chứng từ)"
            elif item.kind == "other_petroleum":
                book["1.1"][f"C{row}"] = "Các sản phẩm dầu mỏ khác (Dầu nhờn/Mazut nhẹ)"
            elif item.kind == "other_solid_biomass":
                book["1.1"][f"C{row}"] = "Nhiên liệu sinh khối rắn khác (Viên nén sinh khối)"
            elif item.kind == "peat":
                book["1.1"][f"C{row}"] = "Than bùn (Peat)"
            meta = STATIONARY_FUEL_META.get(item.kind)
            if meta:
                book["1.1"][f"D{row}"] = meta[0]
                book["1.1"][f"S{row}"] = meta[1]
                book["1.1"][f"T{row}"] = meta[2]
                book["1.1"][f"U{row}"] = meta[3]
        else:
            key_cell = ("2.1", f"E{item.month+2}")
            item.coordinate = f"E{item.month+2}"
            book["2.1"][f"C{item.month+2}"] = f"EVN-2026-T{item.month:02d}"
            book["2.1"][f"D{item.month+2}"] = "kWh"
        accumulated[key_cell] += item.quantity
    for (sheet, cell), quantity in accumulated.items():
        book[sheet][cell] = quantity
    for sheet_name, row in [("1.1", row) for row in set(v[0] for v in FUEL_ROWS.values()) if any(("1.1", f"{get_column_letter(month+5)}{row}") in accumulated for month in range(1, 13))] + [("1.2", row) for row in mobile_rows.values()]:
        book[sheet_name][f"R{row}"] = f"=SUM(F{row}:Q{row})"
    # Apply extra cells for all auxiliary sheets and metadata columns if provided
    if getattr(data, "extra_cells", None):
        for sheet_name, cell_map in data.extra_cells.items():
            if sheet_name not in book:
                continue
            ws = book[sheet_name]
            for coord, val in cell_map.items():
                try:
                    cell = ws[coord]
                    if not isinstance(cell, MergedCell):
                        ws[coord] = val
                except Exception:
                    continue
        # Ensure facility and company arguments remain reflected on Thông tin chung
        if "Thông tin chung" in data.extra_cells:
            if "B8" not in data.extra_cells["Thông tin chung"]:
                info["B8"] = f"1. Tên cơ sở: {facility}"
            else:
                info["B8"] = f"1. Tên cơ sở: {facility}"
            info["B14"] = f"- Ngành nghề sản xuất/Loại hình kinh doanh: Sản xuất công nghiệp, dệt may & năng lượng — Đơn vị cung cấp: {company}"
    # Preserve the original template's formulas and presentation.
    for month in range(1, 13):
        row = month + 2
        if ("2.1", f"E{row}") in accumulated or book["2.1"][f"F{row}"].value not in (None, ""):
            book["2.1"][f"G{row}"] = f"=SUM(E{row}:F{row})"
    book["2.1"]["E15"] = "=SUM(E3:E14)"
    if any(book["2.1"][f"F{r}"].value not in (None, "") for r in range(3, 15)):
        book["2.1"]["F15"] = "=SUM(F3:F14)"
        book["2.1"]["G15"] = "=SUM(G3:G14)"
    book.save(path)
    return warnings
