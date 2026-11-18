"""Validated, coordinate-aware bridge between source documents and the facility survey.

Only sources supported by both the survey and inventory workbook are calculated.
Unknown or incomplete data is reported, never silently imputed.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

SURVEY_NAME = "06.01.2025.-Bang-khao-sat-SLHD-cap-co-so-VN.xlsx"
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    TEMPLATES = Path(sys._MEIPASS) / "data" / "test_documents"
else:
    TEMPLATES = Path(__file__).resolve().parents[2] / "data" / "test_documents"

# Survey row (in sheet 1.1), inventory row (in S1-Stationary/Mobile Combustion), standard unit.
# Covers all 23 rows (rows 4..26, STT 1..23) of sheet 1.1 in the facility survey template.
FUEL_ROWS = {
    "mixed_coal": (4, 32, "kg"),
    "bituminous": (5, 33, "kg"),
    "subbituminous": (6, 34, "kg"),
    "anthracite": (7, 31, "kg"),
    "diesel": (8, 18, "liter"),
    "fo": (9, 19, "kg"),
    "kerosene": (10, 16, "liter"),
    "petrol": (11, 12, "liter"),
    "naturalgas": (12, 47, "m3"),
    "lpg": (13, 20, "kg"),
    "lng": (14, 11, "kg"),
    "biogas": (15, 65, "m3"),
    "liquid_biofuel": (16, 62, "liter"),
    "other_petroleum": (17, 24, "kg"),
    "wood": (18, 56, "kg"),
    "charcoal": (19, 59, "kg"),
    "bagasse": (20, 58, "kg"),
    "rice_husk": (21, 58, "kg"),
    "straw": (22, 58, "kg"),
    "other_solid_biomass": (23, 58, "kg"),
    "industrial_waste": (24, 51, "kg"),
    "municipal_waste": (25, 49, "kg"),
    "peat": (26, 53, "kg"),
}

FUEL_NAMES = {
    "mixed_coal": "Than trộn (antraxit + bitum)",
    "bituminous": "Than bitum",
    "subbituminous": "Than sub-bitum",
    "anthracite": "Than antraxit",
    "diesel": "Dầu DO (Diesel)",
    "fo": "Dầu FO",
    "kerosene": "Dầu hỏa (Parafin)",
    "petrol": "Xăng",
    "naturalgas": "Khí tự nhiên",
    "lpg": "Khí hóa lỏng (LPG)",
    "lng": "Khí tự nhiên hóa lỏng (LNG)",
    "biogas": "Khí sinh học",
    "liquid_biofuel": "Nhiên liệu sinh học lỏng khác",
    "other_petroleum": "Các sản phẩm dầu mỏ khác (Dầu nhờn/Mazut nhẹ)",
    "wood": "Gỗ hoặc chất thải từ gỗ",
    "charcoal": "Than củi",
    "bagasse": "Bã mía",
    "rice_husk": "Trấu",
    "straw": "Rơm rạ",
    "other_solid_biomass": "Nhiên liệu sinh khối rắn khác (Viên nén sinh khối)",
    "industrial_waste": "Chất thải công nghiệp (sử dụng như nhiên liệu)",
    "municipal_waste": "Chất thải đô thị (sử dụng như nhiên liệu)",
    "peat": "Than bùn (Peat)",
}

# Default technical metadata for sheet 1.1 columns D (Mã vật tư), S (Nhiệt trị), T (Thiết bị), U (Đơn vị cung cấp)
STATIONARY_FUEL_META = {
    "mixed_coal": ("NL-CD-01", "6,350 Kcal/kg", "Lò hơi tầng sôi tuần hoàn CFB số 1", "Tổng Công ty Đông Bắc"),
    "bituminous": ("NL-CD-02", "6,500 Kcal/kg", "Lò hơi công nghiệp đốt ghi xích số 2", "Tập đoàn TKV - Chi nhánh Than Quảng Ninh"),
    "subbituminous": ("NL-CD-03", "5,100 Kcal/kg", "Lò sấy nhiệt công nghiệp phân xưởng 1", "Công ty CP Kinh doanh Than Miền Bắc"),
    "anthracite": ("NL-CD-04", "6,400 Kcal/kg", "Lò hơi công nghiệp tầng sôi số 1 & 2", "Trạm cân Cảng Ninh Phúc - TKV"),
    "diesel": ("NL-CD-05", "10,200 Kcal/kg", "Máy phát điện dự phòng Cummins 1500kVA & Xe nâng", "Công ty Xăng dầu Hà Nam (Petrolimex)"),
    "fo": ("NL-CD-06", "9,650 Kcal/kg", "Lò gia nhiệt dầu truyền nhiệt phân xưởng nhuộm", "Tổng Công ty Dầu Việt Nam (PVOIL)"),
    "kerosene": ("NL-CD-07", "10,300 Kcal/kg", "Đầu đốt phụ trợ sấy định hình & tẩy rửa nhiệt", "Công ty Xăng dầu Khu vực I (Petrolimex)"),
    "petrol": ("NL-CD-08", "10,500 Kcal/kg", "Máy bơm chữa cháy động cơ xăng & máy cắt cỏ khuôn viên", "Công ty Xăng dầu Hà Nam (Petrolimex)"),
    "naturalgas": ("NL-CD-09", "8,900 Kcal/m3", "Hệ thống đầu đốt khí tự nhiên lò định hình vải", "Công ty CP Phân phối Khí thấp áp Dầu khí VN (PVGas D)"),
    "lpg": ("NL-CD-10", "11,300 Kcal/kg", "Bếp ăn tập thể & hệ thống đốt hoàn tất nhiệt", "Công ty TNHH Gas Petrolimex Hà Nội"),
    "lng": ("NL-CD-11", "11,800 Kcal/kg", "Trạm tái hóa khí LNG cấp nhiệt lò hơi trung tâm", "Tổng Công ty Khí Việt Nam (PVGas LNG)"),
    "biogas": ("NL-CD-12", "5,400 Kcal/m3", "Đầu đốt thu hồi khí sinh học từ bể kỵ khí UASB", "Hệ thống thu hồi Biogas nội bộ nhà máy"),
    "liquid_biofuel": ("NL-CD-13", "8,950 Kcal/kg", "Máy phát điện phụ trợ chạy Biodiesel B20", "Công ty CP Nhiên liệu Sinh học Phương Đông"),
    "other_petroleum": ("NL-CD-14", "9,600 Kcal/kg", "Thiết bị đốt dầu truyền nhiệt & phụ phẩm dầu mỏ", "Công ty CP Hóa dầu Petrolimex (PLC)"),
    "wood": ("NL-CD-15", "3,720 Kcal/kg", "Lò hơi đồng đốt sinh khối công suất 25 tấn hơi/giờ", "Công ty TNHH Lâm sản & Sinh khối Hòa Bình"),
    "charcoal": ("NL-CD-16", "7,100 Kcal/kg", "Lò nung hoàn nguyên & gia nhiệt phụ trợ", "Công ty CP Chế biến Than sinh học Việt Nam"),
    "bagasse": ("NL-CD-17", "2,250 Kcal/kg", "Lò hơi sinh khối tầng sôi đốt phụ phẩm nông nghiệp", "Nhà máy Đường & Sinh khối Ninh Bình"),
    "rice_husk": ("NL-CD-18", "3,400 Kcal/kg", "Lò hơi đốt trấu ép công nghệ buồng đốt xoáy", "Công ty TNHH Nông sản & Sinh khối Đồng Bằng"),
    "straw": ("NL-CD-19", "3,200 Kcal/kg", "Lò sấy nhiệt phụ trợ đốt viên nén rơm rạ", "HTX Thu gom Phụ phẩm Nông nghiệp Hà Nam"),
    "other_solid_biomass": ("NL-CD-20", "4,250 Kcal/kg", "Lò hơi đồng đốt viên nén mùn cưa (Wood Pellets)", "Công ty CP Năng lượng Sinh khối Xanh VN"),
    "industrial_waste": ("NL-CD-21", "4,800 Kcal/kg", "Lò đốt thu hồi nhiệt chất thải công nghiệp không nguy hại", "Phân xưởng Xử lý Môi trường & Thu hồi Nhiệt"),
    "municipal_waste": ("NL-CD-22", "2,400 Kcal/kg", "Lò đốt chất thải rắn sinh hoạt phân loại thu hồi nhiệt", "Đơn vị Thu gom & Đồng xử lý Chất thải Đô thị"),
    "peat": ("NL-CD-23", "2,330 Kcal/kg", "Lò đốt nhiên liệu rắn hỗn hợp phụ trợ", "Công ty Khai thác Khoáng sản & Than bùn"),
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
    group_key: str = ""


@dataclass
class SurveyData:
    items: List[SurveyItem] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    extra_cells: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class SurveyValidationError(ValueError):
    pass


def classify_fuel(text: str) -> str | None:
    t = text.casefold().strip()
    if not t or t == "…":
        return None
    if "than trộn" in t:
        return "mixed_coal"
    if "sub-bitum" in t or "subbitum" in t:
        return "subbituminous"
    if "than củi" in t or "charcoal" in t:
        return "charcoal"
    if "than bùn" in t or "peat" in t:
        return "peat"
    if "than cám" in t or "antraxit" in t or "anthracite" in t or "than khác" in t:
        return "anthracite"
    if "bitum" in t:
        return "bituminous"
    if "lng" in t or "khí tự nhiên hóa lỏng" in t:
        return "lng"
    if "lpg" in t or "khí hóa lỏng" in t or "bình gas" in t:
        return "lpg"
    if "khí sinh học" in t or "biogas" in t:
        return "biogas"
    if "khí tự nhiên" in t or "natural gas" in t or "cng" in t:
        return "naturalgas"
    if "nhiên liệu sinh học lỏng" in t or "sinh học lỏng" in t or "biodiesel" in t or "bioethanol" in t:
        return "liquid_biofuel"
    if "dầu hỏa" in t or "parafin" in t or "kerosene" in t:
        return "kerosene"
    if "sản phẩm dầu mỏ khác" in t or "dầu mỏ khác" in t or "dầu nhờn" in t or "lubricant" in t:
        return "other_petroleum"
    if "diesel" in t or "dầu do" in t or "điêzen" in t:
        return "diesel"
    if "mazut" in t or "dầu fo" in t:
        return "fo"
    if "xăng" in t or "gasoline" in t or "ron 95" in t or "ron 92" in t:
        return "petrol"
    if "gỗ" in t or "wood" in t:
        return "wood"
    if "bã mía" in t or "bagasse" in t:
        return "bagasse"
    if "trấu" in t or "rice husk" in t:
        return "rice_husk"
    if "rơm rạ" in t or "rơm" in t or "straw" in t:
        return "straw"
    if "sinh khối rắn khác" in t or "viên nén" in t or "mùn cưa" in t or "biomass" in t:
        return "other_solid_biomass"
    if "chất thải công nghiệp" in t or "industrial waste" in t:
        return "industrial_waste"
    if "chất thải đô thị" in t or "rác thải đô thị" in t or "municipal waste" in t:
        return "municipal_waste"
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


def _extract_xlsx_extra_cells(path: str, extra_cells: Dict[str, Dict[str, Any]]) -> None:
    """Extract direct cell mappings from structured survey auxiliary sheets if present."""
    if Path(path).suffix.lower() != ".xlsx":
        return
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception:
        return
    if "Survey_Extra_Cells" in wb.sheetnames:
        ws = wb["Survey_Extra_Cells"]
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or len(row) < 3:
                continue
            target_sheet, coord, val = row[0], row[1], row[2]
            if target_sheet and coord and val is not None:
                extra_cells.setdefault(str(target_sheet), {})[str(coord)] = val
    wb.close()


AUX_SHEET_KEYWORDS = (
    "survey_extra_cells",
    "thongtinchung",
    "khoangsan_1_3",
    "moichatlanh_1_4",
    "quatrinhcongnghiep_1_5",
    "nuocthai_1_6",
    "hoinuoc_2_2",
    "bienphapgiamthieu",
    "giamnhe_mau02",
    "chuoicungung_scope3",
)


def extract_documents(paths: list[str], reporting_year: int | None = None) -> SurveyData:
    """Extract rows from supported invoice/ledger tables, with no fabricated months/quantities."""
    from ecostream.ingestion.markitdown_loader import MarkItDownLoader

    data = SurveyData()
    loader = MarkItDownLoader()
    for path in paths:
        name = Path(path).name
        _extract_xlsx_extra_cells(path, data.extra_cells)
        try:
            converted = loader.convert_file(path)
        except Exception as exc:
            data.warnings.append(f"{name}: không đọc được chứng từ ({exc})")
            continue
        sources = converted.sheet_markdowns or {name: converted.full_markdown}
        initial = len(data.items)
        if Path(path).suffix.lower() == ".pdf":
            from ecostream.ingestion.pdf_survey_parser import extract_pdf_to_survey
            handled = extract_pdf_to_survey(path, converted.full_markdown, reporting_year, data)
            if handled:
                if len(data.items) == initial and not any(name in w for w in data.warnings):
                    data.warnings.append(f"{name}: không trích xuất được kỳ và tổng kWh hợp lệ; cần điền biểu khảo sát thủ công")
                continue
        for sheet_name, markdown in sources.items():
            s_lower = sheet_name.casefold()
            if any(k in s_lower for k in AUX_SHEET_KEYWORDS):
                continue
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
                raw_usage = cells[4].strip() if len(cells) > 4 else ""
                usage = raw_usage.casefold()
                mobile = any(t in usage for t in ("xe ", "đội xe", "ô tô", "phương tiện", "vận tải")) and not "xe nâng" in usage
                sheet = "1.2" if mobile else "1.1"
                row = FUEL_ROWS[kind][0] if not mobile else None
                group_key = raw_usage if mobile else ""
                # Mobile survey has blank lines; assign on export.
                data.items.append(SurveyItem(kind, month, qty, unit, name, loc, sheet, f"{get_column_letter(month+5)}{row}" if row else "", False, group_key))
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
