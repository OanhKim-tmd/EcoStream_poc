"""Validated, coordinate-aware bridge between source documents and the facility survey.

Only sources supported by both the survey and inventory workbook are calculated.
Unknown or incomplete data is reported, never silently imputed.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

SURVEY_NAME = "06.01.2025.-Bang-khao-sat-SLHD-cap-co-so-VN.xlsx"
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    TEMPLATES = Path(sys._MEIPASS) / "data" / "test_documents"
else:
    TEMPLATES = Path(__file__).resolve().parents[2] / "data" / "test_documents"

# Survey row, inventory row, standard unit. Only explicitly verified mappings.
FUEL_ROWS = {
    "diesel": (8, 18, "liter"),
    "petrol": (11, 12, "liter"),
    "lpg": (13, 20, "kg"),
    "fo": (9, 19, "kg"),
    "anthracite": (7, 31, "kg"),
    "bituminous": (5, 33, "kg"),
    "subbituminous": (6, 34, "kg"),
    "naturalgas": (12, 47, "m3"),
}
FUEL_NAMES = {
    "diesel": "Dầu DO (Diesel)", "petrol": "Xăng", "lpg": "Khí hóa lỏng (LPG)",
    "fo": "Dầu FO", "anthracite": "Than antraxit", "bituminous": "Than bitum",
    "subbituminous": "Than sub-bitum", "naturalgas": "Khí tự nhiên",
}


@dataclass
class SurveyItem:
    kind: str
    month: int
    quantity: float
    unit: str
    source_document: str
    source_location: str
    sheet: str
    coordinate: str
    estimated: bool = False


@dataclass
class SurveyData:
    items: List[SurveyItem] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class SurveyValidationError(ValueError):
    pass


def classify_fuel(text: str) -> str | None:
    t = text.casefold()
    if "lpg" in t or "khí hóa lỏng" in t or "bình gas" in t:
        return "lpg"
    if "diesel" in t or "dầu do" in t or "điêzen" in t:
        return "diesel"
    if "mazut" in t or "dầu fo" in t:
        return "fo"
    if "xăng" in t or "gasoline" in t or "ron 95" in t or "ron 92" in t:
        return "petrol"
    if "sub-bitum" in t or "subbitum" in t:
        return "subbituminous"
    if "than trộn" in t or "than khác" in t:
        # Other coal can only map when explicitly relabelled with a known type.
        if "antraxit (theo chứng từ)" not in t:
            return None
    if "bitum" in t:
        return "bituminous"
    if "than cám" in t or "antraxit" in t or "anthracite" in t:
        return "anthracite"
    if "khí tự nhiên" in t or "natural gas" in t:
        return "naturalgas"
    return None


def parse_number(value, coordinate: str) -> float:
    if isinstance(value, bool) or value is None or value == "":
        raise SurveyValidationError(f"{coordinate}: thiếu số lượng")
    if isinstance(value, (int, float)):
        result = float(value)
    else:
        text = str(value).strip().replace(" ", "")
        # 1.234,5 / 1,234.5 / 1,234 / 1.234
        if "," in text and "." in text:
            decimal = "," if text.rfind(",") > text.rfind(".") else "."
            text = text.replace("." if decimal == "," else ",", "").replace(decimal, ".")
        elif re.fullmatch(r"\d{1,3}([.,]\d{3})+", text):
            text = text.replace(".", "").replace(",", "")
        else:
            text = text.replace(",", ".")
        try:
            result = float(text)
        except ValueError as exc:
            raise SurveyValidationError(f"{coordinate}: giá trị không phải số: {value!r}") from exc
    if not (0 <= result < 1e12) or result != result:
        raise SurveyValidationError(f"{coordinate}: số lượng không hợp lệ")
    return result


def normalize_quantity(kind: str, quantity: float, unit: str, location: str) -> tuple[float, str]:
    unit = unit.strip().casefold().replace("³", "3")
    standard = "kWh" if kind == "electricity" else FUEL_ROWS[kind][2]
    if kind == "electricity":
        if unit not in ("kwh", "kw.h", "độ"):
            raise SurveyValidationError(f"{location}: điện mua lưới phải có đơn vị kWh")
        return quantity, standard
    if standard == "liter" and unit in ("l", "lít", "lit", "liter", "litre", "litres"):
        return quantity, standard
    if standard == "kg" and unit in ("kg", "kilogram", "kilograms"):
        return quantity, standard
    if standard == "kg" and unit in ("tấn", "tan", "tonne", "tonnes", "ton"):
        return quantity * 1000, standard
    if standard == "m3" and unit in ("m3", "m^3", "m³"):
        return quantity, standard
    raise SurveyValidationError(f"{location}: đơn vị {unit!r} chưa hỗ trợ cho {FUEL_NAMES[kind]}; cần xác minh")


def _month(value) -> int | None:
    match = re.search(r"(?:tháng|thang|month)\s*0?(1[0-2]|[1-9])\b", str(value), re.I)
    if match:
        return int(match.group(1))
    match = re.search(r"\b(20\d{2})[-/](0?[1-9]|1[0-2])\b", str(value))
    if match:
        return int(match.group(2))
    return None


def extract_documents(paths: list[str], reporting_year: int | None = None) -> SurveyData:
    """Extract rows from supported invoice/ledger tables, with no fabricated months/quantities."""
    from ecostream.ingestion.markitdown_loader import MarkItDownLoader

    data = SurveyData()
    loader = MarkItDownLoader()
    for path in paths:
        name = Path(path).name
        try:
            converted = loader.convert_file(path)
        except Exception as exc:
            data.warnings.append(f"{name}: không đọc được chứng từ ({exc})")
            continue
        sources = converted.sheet_markdowns or {name: converted.full_markdown}
        initial = len(data.items)
        if Path(path).suffix.lower() == ".pdf" and "TIỀN ĐIỆN" in converted.full_markdown.upper():
            # Match only an invoice's explicit billing period and active-energy
            # TOTAL on the same page; do not sum tariff bands or currency figures.
            pages = re.split(r"(?=^## Page \d+)", converted.full_markdown, flags=re.M)
            if len(pages) == 1:
                pages = ["", converted.full_markdown]  # some converters omit the page marker
            for page_no, page in enumerate(pages[1:], 1):
                period = re.search(r"Kỳ:\s*\d+\s*\(Từ ngày\s*\d{2}/(\d{2})/(20\d{2})\s*đến ngày\s*\d{2}/(\d{2})/(20\d{2})", page)
                totals = re.findall(r"Cộng điện năng tác dụng\s*\(Ap\)\s*([\d.,]+)\s*kWh", page, re.I)
                if not period or len(totals) != 1 or period[2] != period[4] or period[1] != period[3]:
                    data.warnings.append(f"{name} trang {page_no}: không xác định duy nhất kỳ và tổng kWh, cần kiểm tra thủ công")
                    continue
                month, year = int(period[1]), int(period[2])
                if reporting_year is not None and year != reporting_year:
                    data.warnings.append(f"{name} trang {page_no}: năm hóa đơn {year} khác năm báo cáo {reporting_year}; bỏ qua")
                    continue
                invoice_no = re.search(r"Số\s*\(No\.\):\s*([A-Za-z0-9-]+)", page)
                loc = f"{name} / trang {page_no} / hóa đơn {invoice_no[1] if invoice_no else 'chưa rõ số'} / Cộng điện năng tác dụng (Ap)"
                try:
                    quantity = parse_number(totals[0], loc)
                except SurveyValidationError as exc:
                    data.warnings.append(str(exc)); continue
                if quantity:
                    data.items.append(SurveyItem("electricity", month, quantity, "kWh", name, loc, "2.1", f"E{month+2}"))
            if len(data.items) == initial:
                data.warnings.append(f"{name}: không trích xuất được kỳ và tổng kWh hợp lệ; cần điền biểu khảo sát thủ công")
            continue
        for sheet_name, markdown in sources.items():
            # Some XLSX converters retain a one-cell title as the first table
            # row while later rows carry all their activity columns. Identify
            # the electricity layout from its actual header (or its labels in
            # the converted text), never from the filename alone.
            electricity_table = bool(
                re.search(r"sản lượng điện tiêu thụ\s*\(kwh\)", markdown, re.I)
                and re.search(r"(?:kỳ hóa đơn|mã công tơ|công tơ demo)", markdown, re.I)
            )
            for line_no, line in enumerate(markdown.splitlines(), 1):
                if not line.strip().startswith("|") or "---" in line:
                    continue
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                lower = line.casefold()
                if "kwh" in lower and any(x in lower for x in ("header", "kỳ hóa đơn", "sản lượng điện")):
                    continue
                month = _month(cells[0]) if cells else None
                if month is None:
                    continue
                loc = f"{name} / {sheet_name} / dòng {line_no}"
                years = {int(y) for y in re.findall(r"\b20\d{2}\b", cells[0])}
                if reporting_year is not None and years and reporting_year not in years:
                    data.warnings.append(f"{loc}: kỳ {sorted(years)} không thuộc năm báo cáo {reporting_year}; bỏ qua")
                    continue
                # Recognized electricity tables may have additional tariff bands.
                # Their total is in column 3; never sum the band or price columns.
                if len(cells) >= 3 and electricity_table and not classify_fuel(cells[1]):
                    try:
                        qty = parse_number(cells[2], loc)
                    except SurveyValidationError:
                        continue
                    if qty > 0:
                        data.items.append(SurveyItem("electricity", month, qty, "kWh", name, loc, "2.1", f"E{month+2}"))
                    continue
                # Fuel ledgers: date | fuel name | quantity | unit | usage | note.
                if len(cells) < 4:
                    continue
                kind = classify_fuel(cells[1])
                if not kind:
                    continue
                quantity_text = cells[2]
                unit_text = cells[3]
                cylinder = re.search(r"(\d+)\s*bình.*?(\d+)\s*kg", quantity_text, re.I)
                if kind == "lpg" and cylinder:
                    raw_qty, unit_text = int(cylinder[1]) * int(cylinder[2]), "kg"
                else:
                    try:
                        raw_qty = parse_number(quantity_text, loc)
                    except SurveyValidationError as exc:
                        data.warnings.append(str(exc)); continue
                try:
                    qty, unit = normalize_quantity(kind, raw_qty, unit_text, loc)
                except SurveyValidationError as exc:
                    data.warnings.append(str(exc)); continue
                usage = cells[4].casefold() if len(cells) > 4 else ""
                mobile = any(t in usage for t in ("xe ", "đội xe", "ô tô", "phương tiện", "vận tải")) and not "xe nâng" in usage
                sheet = "1.2" if mobile else "1.1"
                row = FUEL_ROWS[kind][0] if not mobile else None
                # Mobile survey has blank lines; assign on export.
                data.items.append(SurveyItem(kind, month, qty, unit, name, loc, sheet, f"{get_column_letter(month+5)}{row}" if row else ""))
        if len(data.items) == initial:
            data.warnings.append(f"{name}: chưa trích xuất được số liệu Scope 1/2 có tháng, số lượng và đơn vị; cần điền biểu khảo sát thủ công")
    # Re-uploading the same invoice within a consolidated PDF must not double-count
    # an identical period and quantity. Other same-month invoices may be separate
    # meters: retain those quantities but flag them for human reconciliation.
    unique = []
    seen_electricity = {}
    for item in data.items:
        if item.kind == "electricity":
            key = (item.month, item.quantity)
            existing = seen_electricity.get(key)
            invoice_id = re.search(r"hóa đơn ([A-Za-z0-9-]+) /", item.source_location)
            previous_id = re.search(r"hóa đơn ([A-Za-z0-9-]+) /", existing.source_location) if existing else None
            if existing and existing.source_document != item.source_document and invoice_id and previous_id and invoice_id[1] == previous_id[1]:
                data.warnings.append(f"{item.source_location}: cùng số hóa đơn, tháng và kWh đã xuất hiện trong {existing.source_document}; bỏ dòng trùng")
                continue
            if existing and existing.source_document != item.source_document:
                data.warnings.append(f"{item.source_location}: cùng tháng và kWh trong {existing.source_document} nhưng khác/thiếu số hóa đơn; giữ cả hai, cần đối chiếu công tơ")
            seen_electricity[key] = item
        unique.append(item)
    data.items = unique
    return data


def read_survey(path: str, *, source_name: str | None = None) -> SurveyData:
    try:
        book = load_workbook(path, read_only=True, data_only=False)
        for required in ("Thông tin chung", "1.1", "1.2", "2.1"):
            if required not in book:
                raise SurveyValidationError(f"Thiếu sheet {required!r}; vui lòng dùng đúng biểu khảo sát")
        if "Khối lượng nhiên liệu" not in str(book["1.1"]["B1"].value):
            raise SurveyValidationError("Sheet 1.1 không đúng mẫu khảo sát")
        if "Lượng điện năng" not in str(book["2.1"]["B1"].value):
            raise SurveyValidationError("Sheet 2.1 không đúng mẫu khảo sát")
        data = SurveyData()
        label = source_name or Path(path).name
        for sheet_name in ("1.1", "1.2"):
            sheet = book[sheet_name]
            for row in range(4, 27 if sheet_name == "1.1" else 23):
                name = sheet[f"C{row}"].value
                has_values = any(sheet.cell(row, col).value not in (None, "") for col in range(6, 18))
                if not has_values:
                    continue
                kind = classify_fuel(str(name or ""))
                if not kind:
                    raise SurveyValidationError(f"{sheet_name}!C{row}: nhiên liệu không hỗ trợ: {name!r}")
                unit = sheet[f"E{row}"].value
                if not unit:
                    raise SurveyValidationError(f"{sheet_name}!E{row}: thiếu đơn vị nhiên liệu")
                for month in range(1, 13):
                    cell = sheet.cell(row, month + 5)
                    if cell.value in (None, ""):
                        continue
                    if cell.data_type == "f":
                        raise SurveyValidationError(f"{sheet_name}!{cell.coordinate}: ô nhập liệu chứa công thức, cần nhập số")
                    raw = parse_number(cell.value, f"{sheet_name}!{cell.coordinate}")
                    qty, normalized = normalize_quantity(kind, raw, str(unit), f"{sheet_name}!{cell.coordinate}")
                    if qty:
                        data.items.append(SurveyItem(kind, month, qty, normalized, label, f"{sheet_name}!{cell.coordinate}", sheet_name, cell.coordinate))
        sheet = book["2.1"]
        for month in range(1, 13):
            cell = sheet[f"E{month+2}"]
            if cell.value in (None, ""):
                continue
            if cell.data_type == "f":
                raise SurveyValidationError(f"2.1!{cell.coordinate}: ô lượng điện cần nhập số")
            qty = parse_number(cell.value, f"2.1!{cell.coordinate}")
            unit = sheet[f"D{month+2}"].value
            normalized_qty, normalized = normalize_quantity("electricity", qty, str(unit or ""), f"2.1!{cell.coordinate}")
            if normalized_qty:
                data.items.append(SurveyItem("electricity", month, normalized_qty, normalized, label, f"2.1!{cell.coordinate}", "2.1", cell.coordinate))
        if not data.items:
            raise SurveyValidationError("Biểu khảo sát chưa có số liệu nhiên liệu hoặc điện có thể tính; hãy kiểm tra các sheet 1.1, 1.2 và 2.1")
        # Deliberately do not turn undocumented totals into additional activity rows.
        return data
    except SurveyValidationError:
        raise
    except Exception as exc:
        raise SurveyValidationError(f"Không đọc được biểu khảo sát XLSX: {exc}") from exc
