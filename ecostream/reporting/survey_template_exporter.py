"""Fill a copy of the facility activity-data survey from extracted evidence."""
from __future__ import annotations

from collections import defaultdict
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from ecostream.ingestion.survey_workbook import FUEL_ROWS, SURVEY_NAME, TEMPLATES, SurveyData


def export_survey(data: SurveyData, path: str, facility: str, company: str) -> list[str]:
    book = load_workbook(TEMPLATES / SURVEY_NAME)
    warnings = list(data.warnings)
    info = book["Thông tin chung"]
    info["B8"] = f"1. Tên cơ sở: {facility}"
    info["B14"] = f"- Đơn vị cung cấp: {company}"
    accumulated = defaultdict(float)
    mobile_rows = {}
    for item in data.items:
        if item.sheet == "1.2":
            key = (item.kind, item.unit)
            if key not in mobile_rows:
                row = 4 + len(mobile_rows)
                if row > 21:
                    warnings.append(f"{item.source_location}: quá số dòng phương tiện; chưa đưa vào khảo sát")
                    continue
                mobile_rows[key] = row
                from ecostream.ingestion.survey_workbook import FUEL_NAMES
                book["1.2"][f"C{row}"] = FUEL_NAMES[item.kind]
                book["1.2"][f"E{row}"] = item.unit
            row = mobile_rows[key]
            col = get_column_letter(item.month + 5)
            key_cell = ("1.2", f"{col}{row}")
            item.coordinate = f"{col}{row}"
        elif item.sheet == "1.1":
            row = FUEL_ROWS[item.kind][0]
            col = get_column_letter(item.month + 5)
            key_cell = ("1.1", f"{col}{row}")
            book["1.1"][f"E{row}"] = item.unit
            if item.kind == "anthracite":
                book["1.1"][f"C{row}"] = "Than antraxit (theo chứng từ)"
        else:
            key_cell = ("2.1", f"E{item.month+2}")
            item.coordinate = f"E{item.month+2}"
            book["2.1"][f"D{item.month+2}"] = "kWh"
        accumulated[key_cell] += item.quantity
    for (sheet, cell), quantity in accumulated.items():
        book[sheet][cell] = quantity
    for sheet_name, row in [("1.1", row) for row in set(v[0] for v in FUEL_ROWS.values()) if any(("1.1", f"{get_column_letter(month+5)}{row}") in accumulated for month in range(1,13))] + [("1.2", row) for row in mobile_rows.values()]:
        book[sheet_name][f"R{row}"] = f"=SUM(F{row}:Q{row})"
    # Preserve the original template's formulas and presentation.
    for month in range(1, 13):
        row = month + 2
        if ("2.1", f"E{row}") in accumulated:
            book["2.1"][f"G{row}"] = f"=SUM(E{row}:F{row})"
    book["2.1"]["E15"] = "=SUM(E3:E14)"
    book.save(path)
    return warnings
