#!/usr/bin/env python3
"""Generate realistic, official-style Vietnamese PDF invoices & regulatory dossiers (2026)
covering 100% of fields in Bang_khao_sat_da_dien.xlsx.

Generates 6 multi-page PDF documents in data/samples/pdf_invoices_2026/:
  1. 01_Hoa_don_dien_EVN_12_thang_2026.pdf        (EVN NĐ 70/2025 & TT 32/2025 e-invoices, 12 months + Solar PV)
  2. 02_Hoa_don_nhien_lieu_co_dinh_2026.pdf       (Petrolimex/TKV/PVGas VAT invoices for all 23 stationary fuels, 12 months)
  3. 03_Hoa_don_nhien_lieu_di_dong_2026.pdf       (Fleet fuel VAT invoices for all 18 mobile vehicle groups, 12 months)
  4. 04_Hoa_don_hoi_nuoc_va_moi_chat_lanh_2026.pdf (Purchased steam VAT invoice + Refrigerant R22/R134a/R32 service invoice)
  5. 05_Bao_cao_nuoc_thai_va_qua_trinh_CN_2026.pdf (Wastewater monitoring + Industrial Processes 1.5 + Mining 1.3)
  6. 06_Ho_so_co_so_va_giam_nhe_KNK_2026.pdf       (General Info + Supplementary QC Info + Mitigation Measures A/B/C)

Run from project root:
    python scripts/generate_full_pdf_invoices.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ecostream.ingestion.survey_workbook import STATIONARY_FUEL_META
from scripts.generate_mock_evn_pdf import (
    create_nd70_evn_invoice_story,
    number_to_vietnamese_words,
    register_vietnamese_fonts,
)
from scripts.generate_full_survey_data import (
    MOBILE_FLEET_SPECS,
    STATIONARY_FUEL_SPECS,
    _build_extra_cells,
)

OUT_DIR = ROOT / "data" / "samples" / "pdf_invoices_2026"


def _styles():
    register_vietnamese_fonts()
    fn = "DejaVuSans" if "DejaVuSans" in pdfmetrics.getRegisteredFontNames() else "Helvetica"
    fb = "DejaVuSans-Bold" if "DejaVuSans-Bold" in pdfmetrics.getRegisteredFontNames() else "Helvetica-Bold"
    fi = "DejaVuSans-Oblique" if "DejaVuSans-Oblique" in pdfmetrics.getRegisteredFontNames() else "Helvetica-Oblique"
    dark = colors.HexColor("#1A202C")
    navy = colors.HexColor("#0D47A1")
    red = colors.HexColor("#C62828")
    return {
        "fn": fn, "fb": fb, "fi": fi,
        "title": ParagraphStyle("T", fontName=fb, fontSize=12.5, leading=15, alignment=1, textColor=navy),
        "sub": ParagraphStyle("S", fontName=fb, fontSize=9.5, leading=12, alignment=1, textColor=dark),
        "legal": ParagraphStyle("L", fontName=fi, fontSize=7, leading=9.5, alignment=1, textColor=colors.HexColor("#455A64")),
        "hdr": ParagraphStyle("H", fontName=fb, fontSize=8, leading=10.5, textColor=navy),
        "meta": ParagraphStyle("M", fontName=fn, fontSize=7.5, leading=10, alignment=2, textColor=dark),
        "cell": ParagraphStyle("C", fontName=fn, fontSize=7.2, leading=9.5, textColor=dark),
        "cell_b": ParagraphStyle("CB", fontName=fb, fontSize=7.2, leading=9.5, textColor=dark),
        "cell_c": ParagraphStyle("CC", fontName=fn, fontSize=7.2, leading=9.5, alignment=1, textColor=dark),
        "cell_cb": ParagraphStyle("CCB", fontName=fb, fontSize=7.2, leading=9.5, alignment=1, textColor=dark),
        "cell_r": ParagraphStyle("CR", fontName=fn, fontSize=7.2, leading=9.5, alignment=2, textColor=dark),
        "cell_rb": ParagraphStyle("CRB", fontName=fb, fontSize=7.2, leading=9.5, alignment=2, textColor=dark),
        "red_b": ParagraphStyle("RB", fontName=fb, fontSize=8, leading=10, alignment=2, textColor=red),
        "sec": ParagraphStyle("SEC", fontName=fb, fontSize=9, leading=12, textColor=navy),
    }


def _invoice_header(st, seller_html: str, form_no: str, serial: str, inv_no: str, date_str: str, cqt: str, lookup: str):
    t = Table([[Paragraph(seller_html, st["hdr"]), Paragraph(
        f"<b>Mẫu số (Form):</b> <font color='#0D47A1'><b>{form_no}</b></font><br/>"
        f"<b>Ký hiệu (Serial):</b> <font color='#0D47A1'><b>{serial}</b></font><br/>"
        f"<b>Số (No.):</b> <font color='#C62828'><b>{inv_no}</b></font><br/>"
        f"<b>Ngày lập (Date):</b> {date_str}<br/>"
        f"<b>Mã CQT:</b> {cqt}<br/>"
        f"<b>Mã tra cứu:</b> <b>{lookup}</b>",
        st["meta"],
    )]], colWidths=[305, 220])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return t


def _buyer_box(st, buyer_name: str = "CÔNG TY CỔ PHẦN MAY MẶC ECOGARMENT VIỆT NAM", tax_id: str = "0109283746", address: str = "Lô CN-08, KCN Đồng Văn III, Thị xã Duy Tiên, Tỉnh Hà Nam"):
    rows = [
        [Paragraph("<b>Đơn vị mua hàng:</b>", st["cell"]), Paragraph(f"<b>{buyer_name}</b>", st["cell_b"])],
        [Paragraph("<b>Mã số thuế:</b>", st["cell"]), Paragraph(f"<b>{tax_id}</b> &nbsp;&nbsp;|&nbsp;&nbsp; Hình thức thanh toán: <b>Chuyển khoản (TM/CK)</b>", st["cell"])],
        [Paragraph("<b>Địa chỉ cơ sở:</b>", st["cell"]), Paragraph(address, st["cell"])],
    ]
    t = Table(rows, colWidths=[105, 420])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8F9FA")),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#CFD8DC")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#ECEFF1")),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    return t


def _digital_signature_box(st, seller_name: str, sign_date: str, cert_id: str):
    sig = Table([[
        Paragraph("<b>NGƯỜI MUA HÀNG</b><br/><i>(Ký, ghi rõ họ tên)</i><br/><br/>CÔNG TY CP MAY MẶC ECOGARMENT VN", st["cell_c"]),
        Paragraph(
            f"<b>NGƯỜI BÁN HÀNG - {seller_name}</b><br/>"
            "<i>(Ký số điện tử theo NĐ 70/2025/NĐ-CP & TT 32/2025/TT-BTC)</i><br/><br/>"
            f"<font color='#1B5E20'><b>[✓ CHỮ KÝ SỐ HỢP LỆ & XÁC THỰC CQT]</b><br/>"
            f"<b>Ký bởi: {seller_name}</b><br/>"
            f"Thời điểm ký: {sign_date} | Chứng thư: {cert_id}</font>",
            st["cell_c"],
        ),
    ]], colWidths=[230, 295])
    sig.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (1, 0), (1, 0), 0.75, colors.HexColor("#4CAF50")),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#F1F8E9")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return sig


def build_evn_12_months_pdf(path: Path) -> None:
    st = _styles()
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=30, leftMargin=30, topMargin=22, bottomMargin=22)
    monthly_profiles = {
        1: (28050, 9050, 8150),
        2: (26100, 8420, 7580),
        3: (30130, 9720, 8750),
        4: (32426, 10460, 9414),
        5: (36208, 11680, 10512),
        6: (40176, 12960, 11664),
        7: (41850, 13500, 12150),
        8: (41044, 13240, 11916),
        9: (36642, 11820, 10638),
        10: (33170, 10700, 9630),
        11: (30814, 9940, 8946),
        12: (29636, 9560, 8604),
    }
    story = []
    for m in range(1, 13):
        k_bt, k_cd, k_td = monthly_profiles[m]
        story.extend(create_nd70_evn_invoice_story(
            month=m, year=2026,
            company_name="CÔNG TY CỔ PHẦN MAY MẶC ECOGARMENT VIỆT NAM",
            tax_id="0109283746",
            address="Lô CN-08, KCN Đồng Văn III, Thị xã Duy Tiên, Tỉnh Hà Nam",
            customer_id="PD04000389201",
            meter_id="HN-CTR-0982",
            kwh_bt=k_bt, kwh_cd=k_cd, kwh_td=k_td,
        ))
        solar_kwh = 12000 + m * 450
        story.append(Spacer(1, 3))
        story.append(Paragraph(
            f"<b>Ghi chú điện tự sản xuất, tự dùng (SCADA Solar Rooftop 1.5 MWp):</b> Tháng {m:02d}/2026: <b>{solar_kwh:,} kWh</b> (Không phát lên lưới EVN).",
            st["cell"],
        ))
        if m < 12:
            story.append(PageBreak())
    doc.build(story)


def build_stationary_fuel_pdf(path: Path) -> None:
    st = _styles()
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=28, leftMargin=28, topMargin=22, bottomMargin=22)
    story = []
    seller = (
        "<b>TỔNG CÔNG TY NĂNG LƯỢNG & NHIÊN LIỆU CÔNG NGHIỆP VIỆT NAM</b><br/>"
        "<b>CHI NHÁNH PHÂN PHỐI ĐỒNG BẰNG SÔNG HỒNG (PETROLIMEX / TKV / PVGAS)</b><br/>"
        "<font color='#37474F'>MST: <b>0100107370-012</b> | Đ/c: Số 1 Khâm Thiên, Q. Đống Đa, TP. Hà Nội<br/>"
        "TK: 112000099881 tại Vietcombank Sở Giao Dịch</font>"
    )
    unit_prices = {
        "mixed_coal": 3100, "bituminous": 3200, "subbituminous": 2700, "anthracite": 3500,
        "diesel": 20500, "fo": 16800, "kerosene": 21200, "petrol": 22400,
        "naturalgas": 14500, "lpg": 28000, "lng": 26500, "biogas": 8500,
        "liquid_biofuel": 21500, "other_petroleum": 34000, "wood": 1800, "charcoal": 8200,
        "bagasse": 1400, "rice_husk": 1600, "straw": 1350, "other_solid_biomass": 2900,
        "industrial_waste": 1100, "municipal_waste": 950, "peat": 1900,
    }
    for m in range(1, 13):
        last_day = 28 if m == 2 else (30 if m in (4, 6, 9, 11) else 31)
        story.append(_invoice_header(
            st, seller, "1", "1C26TNL", f"{40000 + m * 17:08d}",
            f"{last_day:02d}/{m:02d}/2026", f"0026CQT0100107370{m:06d}", f"NLCD2026T{m:02d}",
        ))
        story.append(Spacer(1, 4))
        story.append(Paragraph("HÓA ĐƠN GIÁ TRỊ GIA TĂNG (NHIÊN LIỆU ĐỐT CỐ ĐỊNH)", st["title"]))
        story.append(Paragraph(f"Kỳ quyết toán giao nhận: Tháng {m:02d}/2026 (Từ 01/{m:02d}/2026 đến {last_day:02d}/{m:02d}/2026)", st["sub"]))
        story.append(Paragraph("(Khởi tạo theo Nghị định 70/2025/NĐ-CP và Thông tư 32/2025/TT-BTC)", st["legal"]))
        story.append(Spacer(1, 4))
        story.append(_buyer_box(st))
        story.append(Spacer(1, 5))

        rows = [[
            Paragraph("<b>STT</b>", st["cell_cb"]),
            Paragraph("<b>Tên hàng hóa / Nhiên liệu (Mã VT)</b>", st["cell_cb"]),
            Paragraph("<b>ĐVT</b>", st["cell_cb"]),
            Paragraph("<b>Số lượng</b>", st["cell_cb"]),
            Paragraph("<b>Đơn giá</b>", st["cell_cb"]),
            Paragraph("<b>Thành tiền (VNĐ)</b>", st["cell_cb"]),
            Paragraph("<b>Thiết bị sử dụng (Mục 1.1)</b>", st["cell_cb"]),
        ]]
        subtotal = 0
        for idx, (kind, label, base_qty, step_qty, unit) in enumerate(STATIONARY_FUEL_SPECS, 1):
            meta = STATIONARY_FUEL_META[kind]
            qty = base_qty + m * step_qty
            price = unit_prices[kind]
            amt = qty * price
            subtotal += amt
            rows.append([
                Paragraph(str(idx), st["cell_c"]),
                Paragraph(f"{label} ({meta[0]})", st["cell"]),
                Paragraph(unit, st["cell_c"]),
                Paragraph(f"{qty:,}", st["cell_r"]),
                Paragraph(f"{price:,}", st["cell_r"]),
                Paragraph(f"{amt:,}", st["cell_r"]),
                Paragraph(meta[2], st["cell"]),
            ])
        vat = int(round(subtotal * 0.08))
        total = subtotal + vat
        rows.append([
            Paragraph("", st["cell"]),
            Paragraph("<b>Cộng tiền hàng (Chưa GTGT) / Thuế GTGT 8% / Tổng thanh toán:</b>", st["cell_b"]),
            Paragraph("", st["cell"]),
            Paragraph("", st["cell"]),
            Paragraph(f"{subtotal:,}", st["cell_r"]),
            Paragraph(f"<b>{total:,}</b>", st["cell_rb"]),
            Paragraph(f"Thuế GTGT: {vat:,} VNĐ", st["cell"]),
        ])
        tbl = Table(rows, colWidths=[22, 145, 32, 48, 45, 78, 155])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EBF3FB")),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E3F2FD")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B0BEC5")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 1.8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 3))
        story.append(Paragraph(f"<b>Số tiền viết bằng chữ:</b> <i>{number_to_vietnamese_words(total)}</i>", st["cell"]))
        story.append(Spacer(1, 5))
        story.append(_digital_signature_box(st, "CHI NHÁNH PHÂN PHỐI PETROLIMEX - TKV", f"{last_day:02d}/{m:02d}/2026 17:45:10", f"CA-NLCD-2026-{m:02d}"))
        if m < 12:
            story.append(PageBreak())
    doc.build(story)


def build_mobile_fuel_pdf(path: Path) -> None:
    st = _styles()
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=28, leftMargin=28, topMargin=22, bottomMargin=22)
    story = []
    seller = (
        "<b>CÔNG TY XĂNG DẦU HÀ NAM - PETROLIMEX</b><br/>"
        "<font color='#37474F'>MST: <b>0700101234</b> | Đ/c: Quốc lộ 1A, TP. Phủ Lý, Tỉnh Hà Nam<br/>"
        "Cửa hàng Xăng dầu số 08 - KCN Đồng Văn</font>"
    )
    for m in range(1, 13):
        last_day = 28 if m == 2 else (30 if m in (4, 6, 9, 11) else 31)
        story.append(_invoice_header(
            st, seller, "1", "1C26TDD", f"{60000 + m * 23:08d}",
            f"{last_day:02d}/{m:02d}/2026", f"0026CQT0700101234{m:06d}", f"NLDD2026T{m:02d}",
        ))
        story.append(Spacer(1, 4))
        story.append(Paragraph("HÓA ĐƠN GIÁ TRỊ GIA TĂNG (NHIÊN LIỆU PHƯƠNG TIỆN DI ĐỘNG)", st["title"]))
        story.append(Paragraph(f"Bảng kê cấp phát nhiên liệu đội xe vận tải & công vụ — Tháng {m:02d}/2026", st["sub"]))
        story.append(Paragraph("(Khởi tạo theo Nghị định 70/2025/NĐ-CP và Thông tư 32/2025/TT-BTC)", st["legal"]))
        story.append(Spacer(1, 4))
        story.append(_buyer_box(st))
        story.append(Spacer(1, 5))

        rows = [[
            Paragraph("<b>STT</b>", st["cell_cb"]),
            Paragraph("<b>Nhiên liệu (Mã VT)</b>", st["cell_cb"]),
            Paragraph("<b>ĐVT</b>", st["cell_cb"]),
            Paragraph("<b>Số lượng</b>", st["cell_cb"]),
            Paragraph("<b>Đơn giá</b>", st["cell_cb"]),
            Paragraph("<b>Thành tiền</b>", st["cell_cb"]),
            Paragraph("<b>Đội phương tiện / Biển kiểm soát (Mục 1.2)</b>", st["cell_cb"]),
        ]]
        subtotal = 0
        for idx, (kind, label, base_qty, step_qty, unit, vehicle_group) in enumerate(MOBILE_FLEET_SPECS, 1):
            qty = base_qty + m * step_qty
            price = 20500 if kind == "diesel" else 22400
            amt = qty * price
            subtotal += amt
            rows.append([
                Paragraph(str(idx), st["cell_c"]),
                Paragraph(f"{label} (NL-DD-{idx:02d})", st["cell"]),
                Paragraph(unit, st["cell_c"]),
                Paragraph(f"{qty:,}", st["cell_r"]),
                Paragraph(f"{price:,}", st["cell_r"]),
                Paragraph(f"{amt:,}", st["cell_r"]),
                Paragraph(vehicle_group, st["cell"]),
            ])
        vat = int(round(subtotal * 0.08))
        total = subtotal + vat
        rows.append([
            Paragraph("", st["cell"]),
            Paragraph("<b>Tổng cộng thanh toán (đã gồm 8% GTGT):</b>", st["cell_b"]),
            Paragraph("", st["cell"]),
            Paragraph("", st["cell"]),
            Paragraph("", st["cell"]),
            Paragraph(f"<b>{total:,}</b>", st["cell_rb"]),
            Paragraph(f"Tiền hàng: {subtotal:,} | VAT: {vat:,}", st["cell"]),
        ])
        tbl = Table(rows, colWidths=[22, 100, 30, 44, 42, 68, 219])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EBF3FB")),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E3F2FD")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B0BEC5")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 3))
        story.append(Paragraph(f"<b>Số tiền viết bằng chữ:</b> <i>{number_to_vietnamese_words(total)}</i>", st["cell"]))
        story.append(Spacer(1, 5))
        story.append(_digital_signature_box(st, "CÔNG TY XĂNG DẦU HÀ NAM - PETROLIMEX", f"{last_day:02d}/{m:02d}/2026 18:10:00", f"CA-NLDD-2026-{m:02d}"))
        if m < 12:
            story.append(PageBreak())
    doc.build(story)


def build_steam_and_refrigerants_pdf(path: Path) -> None:
    st = _styles()
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=28, leftMargin=28, topMargin=22, bottomMargin=22)
    story = []

    # Page 1: Hóa đơn hơi nước công nghiệp 12 tháng (Mục 2.2)
    seller_steam = (
        "<b>CÔNG TY CỔ PHẦN NĂNG LƯỢNG NHIỆT HƠI KCN ĐỒNG VĂN</b><br/>"
        "<font color='#37474F'>MST: <b>0700812456</b> | Đ/c: Lô E1, KCN Đồng Văn III, Thị xã Duy Tiên, Hà Nam</font>"
    )
    story.append(_invoice_header(st, seller_steam, "1", "1C26THN", "00088126", "31/12/2026", "0026CQT0700812456001", "STEAM2026HN"))
    story.append(Spacer(1, 4))
    story.append(Paragraph("HÓA ĐƠN GIÁ TRỊ GIA TĂNG & BẢNG KÊ HƠI NƯỚC THƯƠNG PHẨM NĂM 2026", st["title"]))
    story.append(Paragraph("(Mục 2.2: Lượng hơi nước đã mua hàng tháng — Kỳ quyết toán 01/2026 – 12/2026)", st["sub"]))
    story.append(Spacer(1, 4))
    story.append(_buyer_box(st))
    story.append(Spacer(1, 5))

    steam_rows = [[
        Paragraph("<b>Tháng</b>", st["cell_cb"]),
        Paragraph("<b>Khối lượng hơi (tấn)</b>", st["cell_cb"]),
        Paragraph("<b>Áp suất (Pa)</b>", st["cell_cb"]),
        Paragraph("<b>Nhiệt độ (oC)</b>", st["cell_cb"]),
        Paragraph("<b>Entanpi (kJ/kg)</b>", st["cell_cb"]),
        Paragraph("<b>Hiệu suất (%)</b>", st["cell_cb"]),
        Paragraph("<b>Tỷ lệ nhiên liệu lò hơi</b>", st["cell_cb"]),
    ]]
    total_steam = 0.0
    for m in range(1, 13):
        mass = round(1450.0 + m * 35.0, 1)
        total_steam += mass
        press = 1050000 + (m % 4) * 25000
        temp = round(182.0 + (m % 5) * 1.2, 1)
        enth = round(2778.0 + (m % 6) * 2.5, 1)
        eff = round(86.0 + (m % 4) * 0.6, 1)
        steam_rows.append([
            Paragraph(f"Tháng {m:02d}/2026", st["cell_c"]),
            Paragraph(f"{mass:,.1f}", st["cell_r"]),
            Paragraph(f"{press:,}", st["cell_r"]),
            Paragraph(f"{temp}", st["cell_r"]),
            Paragraph(f"{enth}", st["cell_r"]),
            Paragraph(f"{eff}", st["cell_r"]),
            Paragraph("80% than bitum, 20% viên nén sinh khối", st["cell"]),
        ])
    steam_rows.append([
        Paragraph("<b>Tổng cộng năm 2026</b>", st["cell_b"]),
        Paragraph(f"<b>{total_steam:,.1f} tấn</b>", st["cell_rb"]),
        Paragraph("TB: 1,081,250", st["cell_r"]),
        Paragraph("TB: 184.2", st["cell_r"]),
        Paragraph("TB: 2,783.6", st["cell_r"]),
        Paragraph("TB: 86.9%", st["cell_r"]),
        Paragraph("Thành tiền: 12,561,000,000 VNĐ (Đã gồm VAT 8%)", st["cell_b"]),
    ])
    t_steam = Table(steam_rows, colWidths=[65, 68, 65, 55, 60, 52, 160])
    t_steam.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EBF3FB")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E3F2FD")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B0BEC5")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_steam)
    story.append(Spacer(1, 8))
    story.append(_digital_signature_box(st, "CÔNG TY CP NĂNG LƯỢNG NHIỆT HƠI ĐỒNG VĂN", "31/12/2026 16:20:00", "CA-STEAM-2026-HN"))

    # Page 2: Hóa đơn nạp môi chất lạnh & Danh sách thiết bị lạnh (Mục 1.4)
    story.append(PageBreak())
    seller_ref = (
        "<b>CÔNG TY CỔ PHẦN CƠ ĐIỆN LẠNH REE & DAIKIN VIỆT NAM</b><br/>"
        "<font color='#37474F'>MST: <b>0300741143</b> | Đ/c: 364 Cộng Hòa, Q. Tân Bình, TP. HCM — CN Hà Nội</font>"
    )
    story.append(_invoice_header(st, seller_ref, "1", "1C26TML", "00033491", "31/12/2026", "0026CQT0300741143009", "REF2026REE"))
    story.append(Spacer(1, 4))
    story.append(Paragraph("HÓA ĐƠN DỊCH VỤ BẢO TRÌ & NẠP MÔI CHẤT LẠNH NĂM 2026 (MỤC 1.4)", st["title"]))
    story.append(Spacer(1, 4))
    story.append(_buyer_box(st))
    story.append(Spacer(1, 5))
    story.append(Paragraph("<b>1. Bảng kê lượng môi chất lạnh tiêu thụ / nạp bổ sung 12 tháng (kg):</b>", st["sec"]))

    ref_data = [
        [Paragraph("<b>Loại môi chất (Mã VT)</b>", st["cell_cb"])] + [Paragraph(f"<b>T{m}</b>", st["cell_cb"]) for m in range(1, 13)] + [Paragraph("<b>Tổng</b>", st["cell_cb"])],
        [Paragraph("R22 (MCL-R22)", st["cell"]), *[Paragraph(str(v), st["cell_r"]) for v in [12.5, 10.0, 15.0, 18.5, 22.0, 25.0, 24.5, 22.0, 18.0, 14.5, 12.0, 11.0]], Paragraph("<b>205.0</b>", st["cell_rb"])],
        [Paragraph("R134a (MCL-R134A)", st["cell"]), *[Paragraph(str(v), st["cell_r"]) for v in [18.0, 16.5, 20.0, 24.0, 28.5, 32.0, 35.0, 31.5, 26.0, 21.0, 18.5, 17.0]], Paragraph("<b>288.0</b>", st["cell_rb"])],
        [Paragraph("R32 (MCL-R32)", st["cell"]), *[Paragraph(str(v), st["cell_r"]) for v in [14.0, 13.0, 16.0, 19.5, 23.0, 27.5, 29.0, 26.5, 21.5, 17.5, 15.0, 13.5]], Paragraph("<b>236.0</b>", st["cell_rb"])],
    ]
    t_ref = Table(ref_data, colWidths=[100] + [31] * 12 + [53])
    t_ref.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EBF3FB")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B0BEC5")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_ref)
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>2. Danh mục thiết bị lạnh thuộc sở hữu cơ sở (AC / Chiller / Kho lạnh):</b>", st["sec"]))
    ac_rows = [[
        Paragraph("<b>STT</b>", st["cell_cb"]),
        Paragraph("<b>Nhãn hiệu & Kiểu máy</b>", st["cell_cb"]),
        Paragraph("<b>Vị trí lắp đặt</b>", st["cell_cb"]),
        Paragraph("<b>Ngày lắp đặt</b>", st["cell_cb"]),
        Paragraph("<b>Môi chất</b>", st["cell_cb"]),
        Paragraph("<b>Công suất</b>", st["cell_cb"]),
        Paragraph("<b>Nạp đầy / Gần nhất</b>", st["cell_cb"]),
    ]]
    for row in [
        ("1", "Trane CVHE-500 Chiller", "Trạm lạnh Xưởng Dệt Nhuộm 1", "15/03/2020", "R134a", "1,750 kW", "320 kg / 45.4 kg (15/06/2026)"),
        ("2", "Daikin VRV RXQ18T (12 tổ)", "Khối văn phòng & Phòng Lab QC", "10/05/2021", "R32", "540 kW", "180 kg / 34.0 kg (20/08/2026)"),
        ("3", "Carrier 30XA Kho hóa chất", "Kho hóa chất nhuộm trung tâm", "01/09/2019", "R22", "820 kW", "210 kg / 22.7 kg (12/04/2026)"),
        ("4", "Emerson Liebert PEX", "Phòng Server & Trung tâm SCADA", "18/11/2022", "R32", "120 kW", "65 kg / 13.5 kg (05/10/2026)"),
    ]:
        ac_rows.append([Paragraph(c, st["cell"]) for c in row])
    t_ac = Table(ac_rows, colWidths=[24, 110, 110, 58, 44, 54, 125])
    t_ac.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EBF3FB")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B0BEC5")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_ac)
    story.append(Spacer(1, 8))
    story.append(_digital_signature_box(st, "CÔNG TY CP CƠ ĐIỆN LẠNH REE", "31/12/2026 15:40:00", "CA-REE-2026-09"))
    doc.build(story)


def build_wastewater_industrial_mining_pdf(path: Path) -> None:
    st = _styles()
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=28, leftMargin=28, topMargin=22, bottomMargin=22)
    story = []
    # Page 1: Báo cáo quan trắc nước thải 12 tháng (Mục 1.6)
    story.append(Paragraph("PHIẾU KẾT QUẢ QUAN TRẮC & VẬN HÀNH TRẠM XỬ LÝ NƯỚC THẢI NĂM 2026 (MỤC 1.6)", st["title"]))
    story.append(Paragraph("Trung tâm Quan trắc Tài nguyên & Môi trường — Chuẩn QCVN 40:2011/BTNMT", st["sub"]))
    story.append(Spacer(1, 4))
    story.append(_buyer_box(st))
    story.append(Spacer(1, 5))
    ww_rows = [[
        Paragraph("<b>Khu vực / Chỉ tiêu</b>", st["cell_cb"]),
        Paragraph("<b>ĐVT</b>", st["cell_cb"]),
        Paragraph("<b>T1</b>", st["cell_cb"]),
        Paragraph("<b>T6</b>", st["cell_cb"]),
        Paragraph("<b>T12</b>", st["cell_cb"]),
        Paragraph("<b>Tổng / TB năm 2026</b>", st["cell_cb"]),
    ]]
    for label, unit, t1, t6, t12, tot in [
        ("Nhà máy 1 - Nước thải công nghiệp", "m3", "18,750", "20,000", "21,500", "241,500 m3"),
        ("Nhà máy 1 - Nước thải sinh hoạt", "m3", "2,435", "2,610", "2,820", "31,530 m3"),
        ("Nhà máy 1 - COD vào/ra (CN)", "mg/lít", "1,265 / 69.2", "1,340 / 75.2", "1,430 / 82.4", "TB: 1,347.5 / 75.8"),
        ("Nhà máy 1 - BOD5 vào/ra (CN)", "mg/lít", "548 / 24.5", "588 / 27.0", "636 / 30.0", "TB: 592.0 / 27.3"),
        ("Nhà máy 1 - CH4 thu hồi UASB", "kg CH4", "432", "492", "564", "5,976 kg CH4"),
        ("Nhà máy 2 - Nước thải công nghiệp", "m3", "14,400", "15,400", "16,600", "186,000 m3"),
        ("Nhà máy 2 - Nước thải sinh hoạt", "m3", "1,875", "2,000", "2,150", "24,150 m3"),
        ("Nhà máy 2 - CH4 thu hồi UASB", "kg CH4", "319", "364", "418", "4,422 kg CH4"),
        ("Khu nhà ở - Nước thải sinh hoạt", "m3", "1,670", "1,770", "1,890", "21,360 m3"),
        ("Khu nhà ở - CH4 thu hồi", "kg CH4", "87.5", "100.0", "115.0", "1,215 kg CH4"),
    ]:
        ww_rows.append([Paragraph(label, st["cell"]), Paragraph(unit, st["cell_c"]), Paragraph(t1, st["cell_r"]), Paragraph(t6, st["cell_r"]), Paragraph(t12, st["cell_r"]), Paragraph(tot, st["cell_rb"])])
    t_ww = Table(ww_rows, colWidths=[175, 48, 65, 65, 65, 107])
    t_ww.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EBF3FB")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B0BEC5")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_ww)
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>Ghi chú kỹ thuật:</b> Hệ thống xử lý nước thải kỵ khí UASB hoạt động liên tục 12 tháng; số liệu đầy đủ từng tháng đã được đính kèm trong hồ sơ quan trắc chi tiết.", st["cell"]))

    # Page 2: Quá trình công nghiệp (Mục 1.5) & Khai thác khoáng sản (Mục 1.3)
    story.append(PageBreak())
    story.append(Paragraph("BÁO CÁO SỐ LIỆU HOẠT ĐỘNG QUÁ TRÌNH CÔNG NGHIỆP & KHAI KHOÁNG NĂM 2026 (MỤC 1.3 & 1.5)", st["title"]))
    story.append(Spacer(1, 5))
    ip_rows = [[
        Paragraph("<b>Nhóm quá trình (Mục)</b>", st["cell_cb"]),
        Paragraph("<b>Sản phẩm / Vật tư / Khoáng sản</b>", st["cell_cb"]),
        Paragraph("<b>ĐVT</b>", st["cell_cb"]),
        Paragraph("<b>Sản lượng / Lượng dùng năm 2026</b>", st["cell_cb"]),
        Paragraph("<b>Ghi chú quy trình</b>", st["cell_cb"]),
    ]]
    for grp, item, unit, val, note in [
        ("1.5 - Khử lưu huỳnh FGD", "CaCO3, MgCO3, CaMg(CO3)2, FeCO3, MnCO3, Na2CO3, Ca(OH)2", "tấn", "4,449.0 (Tổng 8 chất)", "Hấp thụ SO2 khói thải lò hơi CFB"),
        ("1.5 - Sản xuất thép", "Thép BOF (14,500), OHF (6,200), EAF (9,800), Gang (20,500), Quặng thiêu kết & vê viên", "tấn", "103,550 (Tổng 10 chỉ tiêu)", "Phân xưởng luyện kim & cơ khí phụ trợ"),
        ("1.5 - Ngành hóa chất", "Amoniac (8,000), Axit nitric (6,000), CO2 thu hồi (1,150), Than cốc & Antraxit (11,500), Methanol (1,750)", "tấn", "31,262.5 (Tổng 11 chỉ tiêu)", "Tổng hợp hóa chất phụ trợ nhuộm"),
        ("1.5 - Sử dụng sản phẩm", "SF6 máy cắt (146 kg), C2H2 hàn (593 kg), Bình CO2 MT3/MT5 (1,210 kg), Hóa chất XLNT (4,460 kg)", "kg", "6,409.0 (Tổng 5 sản phẩm)", "Trạm 110kV, Đội PCCC & Bảo trì"),
        ("1.3 - Khai thác khoáng sản", "Đá vôi CaCO3 (12,500 tấn), Than antraxit (8,400 tấn), Khí tự nhiên (1,250,000 m3)", "tấn / m3", "Đầy đủ năm 2020, 2022 & 2026", "Khai thác lộ thiên & hầm lò cơ giới hóa"),
    ]:
        ip_rows.append([Paragraph(grp, st["cell_b"]), Paragraph(item, st["cell"]), Paragraph(unit, st["cell_c"]), Paragraph(val, st["cell_r"]), Paragraph(note, st["cell"])])
    t_ip = Table(ip_rows, colWidths=[95, 165, 45, 100, 120])
    t_ip.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EBF3FB")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B0BEC5")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]))
    story.append(t_ip)
    story.append(Spacer(1, 8))
    story.append(_digital_signature_box(st, "PHÒNG KỸ THUẬT & MÔI TRƯỜNG ECOGARMENT", "31/12/2026 17:00:00", "CA-HSE-2026-01"))
    doc.build(story)


def build_general_and_mitigation_pdf(path: Path) -> None:
    st = _styles()
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=28, leftMargin=28, topMargin=22, bottomMargin=22)
    story = []
    story.append(Paragraph("HỒ SƠ THÔNG TIN CƠ SỞ, TÀI LIỆU BỔ SUNG & BIỆN PHÁP GIẢM NHẸ KNK NĂM 2026", st["title"]))
    story.append(Paragraph("(Phục vụ điền mục Thông tin chung, Thông tin bổ sung và Biện pháp giảm thiểu)", st["sub"]))
    story.append(Spacer(1, 5))

    info_rows = [
        [Paragraph("<b>Chỉ mục</b>", st["cell_cb"]), Paragraph("<b>Nội dung khai báo chính thức</b>", st["cell_cb"])],
        [Paragraph("Tên cơ sở", st["cell_b"]), Paragraph("Nhà máy May & Năng lượng Hà Nam — Công ty CP May mặc EcoGarment Việt Nam", st["cell"])],
        [Paragraph("Địa chỉ & Liên hệ", st["cell_b"]), Paragraph("KCN Đồng Văn III, P. Đồng Văn, TX. Duy Tiên, Hà Nam | ĐT: (0226) 3838 999 | contact@ecogarment.vn", st["cell"])],
        [Paragraph("Người đại diện / Người cung cấp", st["cell_b"]), Paragraph("TGĐ Trần Minh Tuấn | Người cung cấp: Nguyễn Văn An (Trưởng phòng HSE, 0912.345.678, an.nguyen@ecogarment.vn)", st["cell"])],
        [Paragraph("Ngành nghề & Trạng thái", st["cell_b"]), Paragraph("Sản xuất dệt may, nhuộm hoàn tất & năng lượng công nghiệp | Đang hoạt động 100% từ năm 2018", st["cell"])],
    ]
    t_info = Table(info_rows, colWidths=[145, 380])
    t_info.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EBF3FB")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B0BEC5")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>Danh mục 13 biện pháp giảm nhẹ phát thải KNK đã & đang triển khai (Nhóm A, B, C):</b>", st["sec"]))
    mit_rows = [[
        Paragraph("<b>Nhóm</b>", st["cell_cb"]),
        Paragraph("<b>Tên biện pháp giảm nhẹ</b>", st["cell_cb"]),
        Paragraph("<b>Chi phí đầu tư</b>", st["cell_cb"]),
        Paragraph("<b>Năm</b>", st["cell_cb"]),
        Paragraph("<b>Hiệu quả / Ghi chú</b>", st["cell_cb"]),
    ]]
    for grp, name, cost, yr, note in [
        ("A - Cải tạo", "Đồng đốt 20% viên nén sinh khối lò hơi CFB", "4.2 tỷ VNĐ", "2025-2026", "Giảm 650 tCO2e/năm"),
        ("A - Cải tạo", "Biến tần VFD quạt gió & máy nén khí", "1.85 tỷ VNĐ", "2025-2026", "Giảm 110 tCO2e/năm"),
        ("A - Cải tạo", "Thu hồi nhiệt khói thải (Economizer)", "2.4 tỷ VNĐ", "2026", "Giảm 320 tCO2e/năm"),
        ("A - Cải tạo", "Thu hồi Biogas CH4 từ bể kỵ khí UASB", "3.1 tỷ VNĐ", "2026", "Giảm 280 tCO2e/năm"),
        ("A - Cải tạo", "Chuyển đổi 10 xe nâng dầu sang xe nâng điện", "5.5 tỷ VNĐ", "2026-2027", "Giảm 145 tCO2e/năm"),
        ("B - Bù trừ", "Điện mặt trời mái nhà Rooftop Solar 1.5 MWp", "16.5 tỷ VNĐ", "2024-2026", "Giảm 770 tCO2e/năm"),
        ("B - Bù trừ", "Hợp đồng mua bán điện trực tiếp DPPA", "2.1 tỷ/năm", "2026-2028", "Bù trừ 1,200 tCO2e/năm"),
        ("B - Bù trừ", "Trồng 15 ha rừng hấp thụ carbon bản địa", "1.2 tỷ VNĐ", "2025-2030", "Hấp thụ 225 tCO2e/năm"),
        ("B - Bù trừ", "Mua tín chỉ carbon VCS / Gold Standard", "850 triệu VNĐ", "2026", "Bù trừ 500 tCO2e/năm"),
        ("C - Tập đoàn", "Quỹ Chuyển đổi Xanh Nội bộ (15 USD/tCO2e)", "3.5 tỷ VNĐ", "2025-2027", "Tập đoàn tài trợ 50% CAPEX"),
        ("C - Tập đoàn", "Quản trị năng lượng ISO 50001 & AI EcoStream", "1.4 tỷ VNĐ", "2026", "Số hóa SCADA & kiểm kê NĐ 06"),
        ("C - Tập đoàn", "Tối ưu logistics ghép tải & nhiên liệu Euro 5", "2.8 tỷ VNĐ", "2026", "Giảm 18% định mức vận tải"),
        ("C - Tập đoàn", "Đào tạo Kiểm kê viên KNK theo TT 17/2022", "450 triệu VNĐ", "2025-2026", "25 kỹ sư được cấp chứng chỉ"),
    ]:
        mit_rows.append([Paragraph(grp, st["cell_b"]), Paragraph(name, st["cell"]), Paragraph(cost, st["cell_r"]), Paragraph(yr, st["cell_c"]), Paragraph(note, st["cell"])])
    t_mit = Table(mit_rows, colWidths=[68, 185, 72, 55, 145])
    t_mit.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EBF3FB")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B0BEC5")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    story.append(t_mit)
    story.append(Spacer(1, 8))
    story.append(_digital_signature_box(st, "ECOGARMENT VIETNAM JSC", "31/12/2026 17:30:00", "CA-ECO-2026-MAIN"))
    doc.build(story)


def generate_all_pdfs(out_dir: Path = OUT_DIR) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    files = [
        out_dir / "01_Hoa_don_dien_EVN_12_thang_2026.pdf",
        out_dir / "02_Hoa_don_nhien_lieu_co_dinh_2026.pdf",
        out_dir / "03_Hoa_don_nhien_lieu_di_dong_2026.pdf",
        out_dir / "04_Hoa_don_hoi_nuoc_va_moi_chat_lanh_2026.pdf",
        out_dir / "05_Bao_cao_nuoc_thai_va_qua_trinh_CN_2026.pdf",
        out_dir / "06_Ho_so_co_so_va_giam_nhe_KNK_2026.pdf",
    ]
    build_evn_12_months_pdf(files[0])
    build_stationary_fuel_pdf(files[1])
    build_mobile_fuel_pdf(files[2])
    build_steam_and_refrigerants_pdf(files[3])
    build_wastewater_industrial_mining_pdf(files[4])
    build_general_and_mitigation_pdf(files[5])

    # Mirror into data/demo_full_2026/pdf_invoices_2026 as well
    demo_pdf_dir = ROOT / "data" / "demo_full_2026" / "pdf_invoices_2026"
    demo_pdf_dir.mkdir(parents=True, exist_ok=True)
    import shutil
    for f in files:
        shutil.copy2(f, demo_pdf_dir / f.name)
    return files


if __name__ == "__main__":
    generated = generate_all_pdfs()
    print("Generated 6 realistic PDF invoice/dossier files:")
    for p in generated:
        print(f"  - {p} ({p.stat().st_size:,} bytes)")
