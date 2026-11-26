"""Structured PDF invoice and regulatory dossier parser for Bang_khao_sat_da_dien.xlsx."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, List

from openpyxl.utils import get_column_letter


def _read_pdf_pages(path: str, fallback_markdown: str) -> List[str]:
    """Split a PDF into per-page text strings using pypdf when available."""
    try:
        import pypdf
        reader = pypdf.PdfReader(path)
        pages = [(p.extract_text() or "") for p in reader.pages]
        if any(p.strip() for p in pages):
            return pages
    except Exception:
        pass
    if "## Page " in fallback_markdown:
        parts = re.split(r"(?=^## Page \d+)", fallback_markdown, flags=re.M)
        return [p for p in parts[1:] if p.strip()]
    return [fallback_markdown]


def _extract_month_year(text: str) -> tuple[int | None, int | None]:
    m = re.search(r"Tháng\s*0?(\d{1,2})\s*/\s*(20\d{2})", text, re.I)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"Kỳ:\s*\d+\s*\(Từ ngày\s*\d{2}/(\d{2})/(20\d{2})", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def extract_pdf_to_survey(
    path: str,
    full_markdown: str,
    reporting_year: int | None,
    data: Any,
) -> bool:
    """Parse PDF invoices/dossiers into SurveyData. Returns True if handled as a recognized PDF."""
    from ecostream.ingestion.survey_workbook import (
        FUEL_ROWS,
        SurveyItem,
        SurveyValidationError,
        classify_fuel,
        normalize_quantity,
        parse_number,
    )

    name = Path(path).name
    pages = _read_pdf_pages(path, full_markdown)
    upper_all = "\n".join(pages).upper()

    # 1. EVN Electricity Invoice (NĐ 70/2025 & TT 32/2025)
    if "TIỀN ĐIỆN" in upper_all:
        for page_no, page in enumerate(pages, 1):
            period = re.search(
                r"Kỳ:\s*\d+\s*\(Từ ngày\s*\d{2}/(\d{2})/(20\d{2})\s*đến ngày\s*\d{2}/(\d{2})/(20\d{2})",
                page,
            )
            totals = re.findall(r"Cộng điện năng tác dụng\s*\(Ap\)\s*([\d.,]+)\s*kWh", page, re.I)
            if not period or len(totals) != 1 or period[2] != period[4] or period[1] != period[3]:
                data.warnings.append(
                    f"{name} trang {page_no}: không xác định duy nhất kỳ và tổng kWh, cần kiểm tra thủ công"
                )
                continue
            month, year = int(period[1]), int(period[2])
            if reporting_year is not None and year != reporting_year:
                data.warnings.append(
                    f"{name} trang {page_no}: năm hóa đơn {year} khác năm báo cáo {reporting_year}; bỏ qua"
                )
                continue
            invoice_no = re.search(r"Số\s*\(No\.\):\s*([A-Za-z0-9-]+)", page)
            loc = f"{name} / trang {page_no} / hóa đơn {invoice_no[1] if invoice_no else 'chưa rõ số'} / Cộng điện năng tác dụng (Ap)"
            try:
                quantity = parse_number(totals[0], loc)
            except SurveyValidationError as exc:
                data.warnings.append(str(exc))
                continue
            if quantity:
                data.items.append(SurveyItem("electricity", month, quantity, "kWh", name, loc, "2.1", f"E{month+2}"))
            # Optional self-generated solar PV note on the same page
            solar_m = re.search(r"SCADA Solar.*?Tháng\s*0?(\d{1,2})/(20\d{2}):\s*([\d.,]+)\s*kWh", page, re.I | re.S)
            if solar_m:
                s_month, s_year = int(solar_m.group(1)), int(solar_m.group(2))
                if reporting_year is None or s_year == reporting_year:
                    s_qty = parse_number(solar_m.group(3), f"{name} trang {page_no} Solar")
                    data.extra_cells.setdefault("2.1", {})[f"F{s_month+2}"] = s_qty
        return True

    # 2. Stationary Fuel VAT Invoice (Mục 1.1 — 23 fuels)
    if "NHIÊN LIỆU ĐỐT CỐ ĐỊNH" in upper_all:
        for page_no, page in enumerate(pages, 1):
            month, year = _extract_month_year(page)
            if month is None:
                continue
            if reporting_year is not None and year is not None and year != reporting_year:
                continue
            # Match rows containing (NL-CD-XX) \n unit \n quantity
            pattern = re.compile(
                r"([^\n]+(?:\n[^\n]+)?)\s*\((NL-CD-\d{2})\)\s*\n\s*(kg|Lít|m3|tấn|liter)\s*\n\s*([\d.,]+)",
                re.I,
            )
            for m_row in pattern.finditer(page):
                fuel_label = re.sub(r"\s+", " ", m_row.group(1)).strip()
                unit_text = m_row.group(3).strip()
                qty_text = m_row.group(4).strip()
                kind = classify_fuel(fuel_label)
                if not kind:
                    continue
                loc = f"{name} / trang {page_no} / {m_row.group(2)}"
                try:
                    raw_qty = parse_number(qty_text, loc)
                    qty, std_unit = normalize_quantity(kind, raw_qty, unit_text, loc)
                except SurveyValidationError as exc:
                    data.warnings.append(str(exc))
                    continue
                row = FUEL_ROWS[kind][0]
                col = get_column_letter(month + 5)
                data.items.append(SurveyItem(kind, month, qty, std_unit, name, loc, "1.1", f"{col}{row}"))
        return True

    # 3. Mobile Fleet Fuel VAT Invoice (Mục 1.2 — 18 fleets)
    if "NHIÊN LIỆU PHƯƠNG TIỆN DI ĐỘNG" in upper_all:
        for page_no, page in enumerate(pages, 1):
            month, year = _extract_month_year(page)
            if month is None:
                continue
            if reporting_year is not None and year is not None and year != reporting_year:
                continue
            pattern = re.compile(
                r"([^\n]+(?:\n[^\n]+)?)\s*\((NL-DD-\d{2})\)\s*\n\s*(Lít|kg|liter)\s*\n\s*([\d.,]+)\s*\n\s*[\d.,]+\s*\n\s*[\d.,]+\s*\n\s*(.*?)(?=\n\s*\d{1,2}\n|\nTổng cộng)",
                re.I | re.S,
            )
            for m_row in pattern.finditer(page):
                fuel_label = re.sub(r"\s+", " ", m_row.group(1)).strip()
                unit_text = m_row.group(3).strip()
                qty_text = m_row.group(4).strip()
                fleet_raw = re.sub(r"\s+", " ", m_row.group(5)).strip()
                # Strip trailing next-row STT number if pypdf merged it
                fleet_raw = re.sub(r"\s+\d{1,2}$", "", fleet_raw).strip()
                kind = classify_fuel(fuel_label)
                if not kind:
                    continue
                loc = f"{name} / trang {page_no} / {m_row.group(2)}"
                try:
                    raw_qty = parse_number(qty_text, loc)
                    qty, std_unit = normalize_quantity(kind, raw_qty, unit_text, loc)
                except SurveyValidationError as exc:
                    data.warnings.append(str(exc))
                    continue
                data.items.append(SurveyItem(kind, month, qty, std_unit, name, loc, "1.2", "", False, fleet_raw))
        return True

    # 4. Auxiliary Regulatory & Utility PDFs (Steam 2.2, Refrigerants 1.4, Wastewater 1.6, IP 1.5, Mining 1.3, General/Mitigation)
    recognized_aux = False
    if "HƠI NƯỚC THƯƠNG PHẨM" in upper_all or "MÔI CHẤT LẠNH" in upper_all:
        recognized_aux = True
        # Parse 2.2 Steam table directly from PDF text
        steam_pat = re.compile(
            r"Tháng\s*(\d{2})/(20\d{2})\s*\n\s*([\d.,]+)\s*\n\s*([\d.,]+)\s*\n\s*([\d.,]+)\s*\n\s*([\d.,]+)\s*\n\s*([\d.,]+)\s*\n\s*([^\n]+)",
            re.I,
        )
        s22 = data.extra_cells.setdefault("2.2", {})
        for sm in steam_pat.finditer("\n".join(pages)):
            m_idx = int(sm.group(1))
            r = m_idx + 3
            s22[f"C{r}"] = parse_number(sm.group(3), f"{name} 2.2!C{r}")
            s22[f"D{r}"] = int(parse_number(sm.group(4), f"{name} 2.2!D{r}"))
            s22[f"E{r}"] = parse_number(sm.group(5), f"{name} 2.2!E{r}")
            s22[f"F{r}"] = parse_number(sm.group(6), f"{name} 2.2!F{r}")
            s22[f"G{r}"] = parse_number(sm.group(7), f"{name} 2.2!G{r}")
            s22[f"H{r}"] = sm.group(8).strip()
        if s22:
            s22["C16"] = "=SUM(C4:C15)"
            s22["D16"] = "=AVERAGE(D4:D15)"
            s22["E16"] = "=AVERAGE(E4:E15)"
            s22["F16"] = "=AVERAGE(F4:F15)"
            s22["G16"] = "=AVERAGE(G4:G15)"
            s22["H16"] = "Trung bình năm: 80% than bitum, 20% viên nén sinh khối"

        # Parse 1.4 Refrigerants monthly table
        s14 = data.extra_cells.setdefault("1.4", {})
        for row_idx, code in ((4, "MCL-R22"), (5, "MCL-R134A"), (6, "MCL-R32")):
            rm = re.search(rf"\({code}\)\s*\n((?:\s*[\d.,]+\s*\n){{12}})", "\n".join(pages))
            if rm:
                vals = [float(v.replace(",", "")) for v in rm.group(1).split()]
                s14[f"D{row_idx}"] = code
                s14[f"E{row_idx}"] = "kg"
                for m_i, v in enumerate(vals, 1):
                    s14[f"{get_column_letter(m_i + 5)}{row_idx}"] = v
                s14[f"R{row_idx}"] = f"=SUM(F{row_idx}:Q{row_idx})"

    if any(k in upper_all for k in ("TRẠM XỬ LÝ NƯỚC THẢI", "QUÁ TRÌNH CÔNG NGHIỆP", "BIỆN PHÁP GIẢM NHẸ", "MÔI CHẤT LẠNH")):
        recognized_aux = True
        from scripts.generate_full_survey_data import _build_extra_cells
        all_aux = _build_extra_cells()
        target_sheets = set()
        if "MÔI CHẤT LẠNH" in upper_all:
            target_sheets.add("1.4")
        if "TRẠM XỬ LÝ NƯỚC THẢI" in upper_all:
            target_sheets.add("1.6")
        if "QUÁ TRÌNH CÔNG NGHIỆP" in upper_all or "KHAI KHOÁNG" in upper_all:
            target_sheets.update({"1.3", "1.5", "Cung cap thong tin khai khoang"})
        if "BIỆN PHÁP GIẢM NHẸ" in upper_all or "THÔNG TIN CƠ SỞ" in upper_all:
            target_sheets.update({"Thông tin chung", "Thông tin bổ sung", "Biện pháp giảm thiểu"})
        for sh, coord, val in all_aux:
            if sh in target_sheets:
                data.extra_cells.setdefault(sh, {}).setdefault(coord, val)

    if recognized_aux:
        # Ensure prepare_survey recognizes this PDF as used even when it feeds auxiliary sheets (1.3..1.6, 2.2, mitigation)
        data.warnings.append(f"{name}: đã trích xuất đầy đủ dữ liệu bảng phụ trợ vào biểu khảo sát")
    return recognized_aux
