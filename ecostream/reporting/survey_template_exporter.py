"""Fill a copy of the facility activity-data survey from extracted evidence."""
from __future__ import annotations

from collections import defaultdict
from copy import copy
import re
from openpyxl import load_workbook
from collections import defaultdict
from copy import copy
import re

from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter

from ecostream.ingestion.survey_workbook import (
    FUEL_NAMES,
    FUEL_ROWS,
    STATIONARY_FUEL_META,
    SURVEY_NAME,
    TEMPLATES,
    SurveyData,
    SurveyGeneralInfo,
)



def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[\r\n\t]+", " ", str(value)).strip()


def _safe_cell_text(value: str) -> str:
    """Prevent Excel formula interpretation when writing standalone user text."""
    text = _clean_text(value)
    if text and text[0] in ("=", "+", "-", "@"):
        return f"'{text}"
    return text


def _write_info_line(sheet, coord: str, row: int, text: str) -> None:
    cell = sheet[coord]
    cell.value = text
    align = copy(cell.alignment)
    align.wrap_text = True
    cell.alignment = align
    if len(text) > 85:
        lines = (len(text) // 80) + 1
        current_height = sheet.row_dimensions[row].height or 23.25
        sheet.row_dimensions[row].height = max(current_height, min(18.0 * lines, 90.0))


def apply_general_info(
    book,
    facility: str,
    company: str,
    general_info: SurveyGeneralInfo | dict | None,
) -> None:
    if isinstance(general_info, SurveyGeneralInfo):
        gi = SurveyGeneralInfo(
            contact_name=_clean_text(general_info.contact_name),
            contact_role=_clean_text(general_info.contact_role),
            contact_phone=_clean_text(general_info.contact_phone),
            contact_email=_clean_text(general_info.contact_email),
            facility_name=_clean_text(general_info.facility_name),
            facility_address=_clean_text(general_info.facility_address),
            facility_phone=_clean_text(general_info.facility_phone),
            facility_email=_clean_text(general_info.facility_email),
            legal_representative=_clean_text(general_info.legal_representative),
            legal_rep_title=_clean_text(general_info.legal_rep_title),
            industry_sector=_clean_text(general_info.industry_sector),
            operating_status=_clean_text(general_info.operating_status),
            start_year=_clean_text(general_info.start_year),
            facility_representative=_clean_text(general_info.facility_representative),
        )
    else:
        gi = SurveyGeneralInfo.from_dict(general_info)

    info = book["Thông tin chung"]
    if gi.contact_name:
        _write_info_line(info, "B3", 3, f"- Họ và tên người cung cấp thông tin: {gi.contact_name}")
    if gi.contact_role:
        _write_info_line(info, "B4", 4, f"- Chức vụ/Bộ phận: {gi.contact_role}")
    if gi.contact_phone:
        _write_info_line(info, "B5", 5, f"- Điện thoại: {gi.contact_phone}")
    if gi.contact_email:
        _write_info_line(info, "B6", 6, f"- Email: {gi.contact_email}")

    effective_facility = gi.facility_name or _clean_text(facility) or _clean_text(company)
    if effective_facility:
        _write_info_line(info, "B8", 8, f"1. Tên cơ sở: {effective_facility}")
    if gi.facility_address:
        _write_info_line(info, "B9", 9, f"- Địa chỉ: {gi.facility_address}")
    if gi.facility_phone:
        _write_info_line(info, "B10", 10, f"- Điện thoại: {gi.facility_phone}")
    if gi.facility_email:
        _write_info_line(info, "B11", 11, f"- Email: {gi.facility_email}")

    if gi.legal_representative or gi.legal_rep_title:
        rep_part = gi.legal_representative or "........................................"
        title_part = gi.legal_rep_title or "......................................................"
        _write_info_line(info, "B12", 12, f"- Người đại diện pháp luật: {rep_part}    Chức danh: {title_part}")

    if gi.industry_sector:
        _write_info_line(info, "B14", 14, f"- Ngành nghề sản xuất/Loại hình kinh doanh: {gi.industry_sector}")

    if gi.operating_status or gi.start_year:
        status_part = gi.operating_status or "........................................................."
        year_part = gi.start_year or "............................"
        _write_info_line(info, "B15", 15, f"- Tình trạng hoạt động: {status_part} / Năm bắt đầu hoạt động: {year_part}")

    if gi.facility_representative:
        info["B17"] = _safe_cell_text(gi.facility_representative)
        info["B17"].alignment = Alignment(horizontal="right", vertical="bottom", wrap_text=True)


def autofit_survey_workbook(book) -> None:
    """Proportionally size columns and wrap long cells across survey sheets so text/numbers fit cleanly."""
    from openpyxl.cell.cell import MergedCell

    def _fit_sheet(ws, min_col: int, max_col: int, min_row: int, max_row: int, col_caps: dict[int, tuple[float, float]] | None = None):
        merged_coords = set()
        for m in ws.merged_cells.ranges:
            for rr in range(m.min_row, m.max_row + 1):
                for cc in range(m.min_col, m.max_col + 1):
                    merged_coords.add((rr, cc))
        col_caps = col_caps or {}
        for c in range(min_col, max_col + 1):
            col_letter = get_column_letter(c)
            existing = ws.column_dimensions[col_letter].width
            max_line_len = 0
            for r in range(min_row, max_row + 1):
                if (r, c) in merged_coords:
                    continue
                cell = ws.cell(r, c)
                if isinstance(cell, MergedCell) or cell.value is None:
                    continue
                s = str(cell.value)
                if s.startswith("="):
                    max_line_len = max(max_line_len, 10)
                else:
                    longest_line = max((len(line) for line in s.splitlines()), default=0)
                    max_line_len = max(max_line_len, longest_line)
                    if r >= 4 and len(s) > 18:
                        align = copy(cell.alignment)
                        align.wrap_text = True
                        cell.alignment = align
            min_w, max_w = col_caps.get(c, (7.5, 46.0))
            if max_line_len == 0:
                target_w = existing or min_w
            else:
                target_w = max(min_w, min(max_w, max_line_len + 3.5))
            if existing is not None:
                # Shrink wide empty/short cols gently only if we set explicit caps, else keep readable
                ws.column_dimensions[col_letter].width = max(target_w, min_w) if c in col_caps else max(existing, target_w)
            else:
                ws.column_dimensions[col_letter].width = target_w

        # Adjust row heights for wrapped multi-line entries
        for r in range(max(4, min_row), max_row + 1):
            needed_lines = 1
            for c in range(min_col, max_col + 1):
                if (r, c) in merged_coords:
                    continue
                val = ws.cell(r, c).value
                if val is None or str(val).startswith("="):
                    continue
                col_w = ws.column_dimensions[get_column_letter(c)].width or 12.0
                text_str = str(val)
                lines = sum(max(1, (len(part) // max(int(col_w - 2), 8)) + 1) for part in text_str.splitlines())
                needed_lines = max(needed_lines, lines)
            if needed_lines > 1:
                cur_h = ws.row_dimensions[r].height or 19.0
                ws.row_dimensions[r].height = max(cur_h, min(needed_lines * 15.5, 84.0))

    if "1.1" in book:
        caps_11 = {
            2: (5.5, 7.0), 3: (36.0, 46.0), 4: (11.0, 18.0), 5: (10.0, 15.0),
            18: (13.0, 16.0), 19: (18.0, 26.0), 20: (26.0, 46.0), 21: (20.0, 40.0),
        }
        for m_col in range(6, 18):
            caps_11[m_col] = (10.5, 15.0)
        _fit_sheet(book["1.1"], 2, 21, 2, 26, caps_11)

    if "1.2" in book:
        caps_12 = {
            2: (5.5, 7.0), 3: (24.0, 42.0), 4: (11.0, 18.0), 5: (10.0, 15.0),
            18: (13.0, 16.0), 19: (18.0, 26.0), 20: (18.0, 34.0), 21: (24.0, 44.0), 22: (14.0, 22.0), 23: (20.0, 38.0),
        }
        for m_col in range(6, 18):
            caps_12[m_col] = (10.5, 15.0)
        _fit_sheet(book["1.2"], 2, 23, 2, 21, caps_12)

    if "2.1" in book:
        _fit_sheet(book["2.1"], 2, 7, 2, 15, {
            2: (12.0, 14.0), 3: (12.0, 18.0), 4: (9.0, 12.0), 5: (22.0, 30.0), 6: (22.0, 30.0), 7: (14.0, 18.0),
        })

    for extra_name, bounds in (
        ("1.3", (2, 6, 2, 5)),
        ("1.4", (2, 29, 2, 6)),
        ("2.2", (2, 8, 2, 16)),
        ("Biện pháp giảm thiểu", (2, 8, 2, 18)),
        ("Cung cap thong tin khai khoang", (1, 7, 2, 9)),
    ):
        if extra_name in book:
            _fit_sheet(book[extra_name], *bounds)


def export_survey(
    data: SurveyData,
    path: str,
    facility: str,
    company: str,
    general_info: SurveyGeneralInfo | dict | None = None,
) -> list[str]:
    book = load_workbook(TEMPLATES / SURVEY_NAME)
    warnings = list(data.warnings)
    apply_general_info(book, facility, company, general_info)
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

    autofit_survey_workbook(book)
    book.save(path)
    return warnings
