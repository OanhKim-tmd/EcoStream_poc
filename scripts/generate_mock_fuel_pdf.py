#!/usr/bin/env python3
"""
Generate synthetic 12-month Vietnamese Fuel VAT E-Invoice PDFs (Hóa đơn GTGT Xăng dầu giả lập)
following the official layout structure of Vietnamese e-invoices (Nghị định 123/2020/NĐ-CP,
Nghị định 70/2025/NĐ-CP, Thông tư 32/2025/TT-BTC).

ALL entities, tax IDs, serial numbers, and signatures are explicitly fictional/synthetic
for software testing and EcoStream demonstration ONLY — NOT valid tax or legal documents.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def register_vietnamese_fonts() -> tuple[str, str, str]:
    """Register TrueType fonts supporting full Vietnamese Unicode diacritics."""
    candidates = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"),
        ("/System/Library/Fonts/Supplemental/Arial.ttf",
         "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
         "/System/Library/Fonts/Supplemental/Arial Italic.ttf"),
        ("C:/Windows/Fonts/arial.ttf",
         "C:/Windows/Fonts/arialbd.ttf",
         "C:/Windows/Fonts/ariali.ttf"),
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf"),
    ]
    for reg, bold, italic in candidates:
        if os.path.exists(reg):
            if "FuelSans" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("FuelSans", reg))
            if os.path.exists(bold) and "FuelSans-Bold" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("FuelSans-Bold", bold))
            if os.path.exists(italic) and "FuelSans-Italic" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("FuelSans-Italic", italic))
            return (
                "FuelSans",
                "FuelSans-Bold" if "FuelSans-Bold" in pdfmetrics.getRegisteredFontNames() else "FuelSans",
                "FuelSans-Italic" if "FuelSans-Italic" in pdfmetrics.getRegisteredFontNames() else "FuelSans",
            )
    return "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"


def format_vn_number(value: float, decimals: int = 0) -> str:
    """Format number in Vietnamese style: dot for thousands, comma for decimal."""
    if decimals > 0:
        raw = f"{value:,.{decimals}f}"
    else:
        raw = f"{int(round(value)):,}"
    # Swap ',' and '.' -> 1,234.56 becomes 1.234,56
    return raw.replace(",", "_").replace(".", ",").replace("_", ".")


def number_to_vietnamese_words(n: int) -> str:
    if n == 0:
        return "Không đồng"
    digits = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]

    def read_three(num: int, show_zero_hundred: bool = False) -> str:
        h = num // 100
        t = (num % 100) // 10
        u = num % 10
        parts = []
        if h > 0 or show_zero_hundred:
            parts.append(f"{digits[h]} trăm")
        if t > 1:
            parts.append(f"{digits[t]} mươi")
            if u == 1:
                parts.append("mốt")
            elif u == 4:
                parts.append("tư")
            elif u == 5:
                parts.append("lăm")
            elif u > 0:
                parts.append(digits[u])
        elif t == 1:
            parts.append("mười")
            if u == 5:
                parts.append("lăm")
            elif u > 0:
                parts.append(digits[u])
        elif t == 0 and u > 0:
            if h > 0 or show_zero_hundred:
                parts.append(f"lẻ {digits[u]}")
            else:
                parts.append(digits[u])
        return " ".join(parts)

    billions = n // 1_000_000_000
    millions = (n % 1_000_000_000) // 1_000_000
    thousands = (n % 1_000_000) // 1_000
    units = n % 1_000

    res = []
    if billions > 0:
        res.append(f"{read_three(billions)} tỷ")
    if millions > 0:
        res.append(f"{read_three(millions, bool(res))} triệu")
    if thousands > 0:
        res.append(f"{read_three(thousands, bool(res))} nghìn")
    if units > 0:
        res.append(read_three(units, bool(res)))
    res.append("đồng")
    text = " ".join(res).strip()
    return text[0].upper() + text[1:]


# Default 12-month synthetic fuel consumption profile for a medium factory
DEFAULT_MONTHLY_FUEL_PROFILE: Dict[int, List[dict]] = {
    1: [
        {"name": "Xăng RON 95-III (Đội xe vận tải)", "unit": "Lít", "qty": 312.50, "price": 21450},
        {"name": "Dầu Điêzen DO 0,05S (Máy phát điện & Lò hơi)", "unit": "Lít", "qty": 1240.00, "price": 19800},
    ],
    2: [
        {"name": "Xăng RON 95-III (Đội xe vận tải)", "unit": "Lít", "qty": 248.20, "price": 21600},
        {"name": "Dầu Điêzen DO 0,05S (Máy phát điện & Lò hơi)", "unit": "Lít", "qty": 980.00, "price": 19950},
    ],
    3: [
        {"name": "Xăng RON 95-III (Đội xe vận tải)", "unit": "Lít", "qty": 335.80, "price": 21850},
        {"name": "Dầu Điêzen DO 0,05S (Máy phát điện & Lò hơi)", "unit": "Lít", "qty": 1350.00, "price": 20100},
    ],
    4: [
        {"name": "Xăng RON 95-III (Đội xe vận tải)", "unit": "Lít", "qty": 324.40, "price": 22100},
        {"name": "Dầu Điêzen DO 0,05S (Máy phát điện & Lò hơi)", "unit": "Lít", "qty": 1290.00, "price": 20300},
    ],
    5: [
        {"name": "Xăng RON 95-III (Đội xe vận tải)", "unit": "Lít", "qty": 348.60, "price": 22350},
        {"name": "Dầu Điêzen DO 0,05S (Máy phát điện & Lò hơi)", "unit": "Lít", "qty": 1420.00, "price": 20450},
    ],
    6: [
        {"name": "Xăng RON 95-III (Đội xe vận tải)", "unit": "Lít", "qty": 362.10, "price": 22500},
        {"name": "Dầu Điêzen DO 0,05S (Máy phát điện & Lò hơi)", "unit": "Lít", "qty": 1510.00, "price": 20600},
    ],
    7: [
        {"name": "Xăng RON 95-III (Đội xe vận tải)", "unit": "Lít", "qty": 374.50, "price": 22400},
        {"name": "Dầu Điêzen DO 0,05S (Máy phát điện & Lò hơi)", "unit": "Lít", "qty": 1580.00, "price": 20550},
    ],
    8: [
        {"name": "Xăng RON 95-III (Đội xe vận tải)", "unit": "Lít", "qty": 359.00, "price": 22250},
        {"name": "Dầu Điêzen DO 0,05S (Máy phát điện & Lò hơi)", "unit": "Lít", "qty": 1490.00, "price": 20400},
    ],
    9: [
        {"name": "Xăng RON 95-III (Đội xe vận tải)", "unit": "Lít", "qty": 341.75, "price": 21950},
        {"name": "Dầu Điêzen DO 0,05S (Máy phát điện & Lò hơi)", "unit": "Lít", "qty": 1380.00, "price": 20150},
    ],
    10: [
        {"name": "Xăng RON 95-III (Đội xe vận tải)", "unit": "Lít", "qty": 328.90, "price": 21700},
        {"name": "Dầu Điêzen DO 0,05S (Máy phát điện & Lò hơi)", "unit": "Lít", "qty": 1310.00, "price": 19900},
    ],
    11: [
        {"name": "Xăng RON 95-III (Đội xe vận tải)", "unit": "Lít", "qty": 336.40, "price": 21550},
        {"name": "Dầu Điêzen DO 0,05S (Máy phát điện & Lò hơi)", "unit": "Lít", "qty": 1340.00, "price": 19850},
    ],
    12: [
        {"name": "Xăng RON 95-III (Đội xe vận tải)", "unit": "Lít", "qty": 378.20, "price": 21800},
        {"name": "Dầu Điêzen DO 0,05S (Máy phát điện & Lò hơi)", "unit": "Lít", "qty": 1540.00, "price": 20050},
    ],
}


def build_fuel_invoice_story(
    month: int,
    year: int = 2026,
    items: Optional[List[dict]] = None,
    buyer_name: str = "CƠ SỞ KIỂM THỬ ECOGARMENT (MẪU GIẢ LẬP)",
    buyer_address: str = "Lô CN-08, Khu Công nghiệp Giả Lập, Hà Nội",
    buyer_tax_id: str = "0000000001",
    seller_name: str = "CÔNG TY XĂNG DẦU MẪU GIẢ LẬP ECOSTREAM",
    seller_address: str = "Trạm cấp phát xăng dầu mẫu số 01, Khu thử nghiệm, Hà Nội",
    seller_tax_id: str = "0000000000",
    seller_phone: str = "0000 000 000",
    payment_mode: str = "Chuyển khoản",
) -> List:
    font_n, font_b, font_i = register_vietnamese_fonts()
    if items is None:
        items = DEFAULT_MONTHLY_FUEL_PROFILE[month]

    # Colors inspired by Vietnamese Fuel VAT E-Invoice form
    navy = colors.HexColor("#1E3A8A")
    blue_label = colors.HexColor("#1D4ED8")
    red_title = colors.HexColor("#DC2626")
    ink = colors.HexColor("#0F172A")
    muted = colors.HexColor("#475569")
    border_blue = colors.HexColor("#1D4ED8")
    grid_line = colors.HexColor("#94A3B8")
    soft_tint = colors.HexColor("#EFF6FF")

    last_day = 28 if month == 2 and year % 4 != 0 else (29 if month == 2 else (30 if month in (4, 6, 9, 11) else 31))
    invoice_day = min(25, last_day)
    invoice_no = f"0000{month:02d}{year % 100:02d}"
    serial_code = f"DEMO-1C{year % 100:02d}XD"
    cqt_code = f"DEMO-{year % 100:02d}-TEST-000{month:02d}{invoice_no}"

    s_top_notice = ParagraphStyle("TopNotice", fontName=font_b, fontSize=7.5, leading=10, alignment=1, textColor=navy)
    s_title = ParagraphStyle("TitleRed", fontName=font_b, fontSize=14, leading=17, alignment=1, textColor=red_title)
    s_subtitle = ParagraphStyle("SubtitleRed", fontName=font_n, fontSize=9.5, leading=12, alignment=1, textColor=red_title)
    s_date = ParagraphStyle("DateStyle", fontName=font_n, fontSize=9, leading=12, alignment=1, textColor=ink)
    s_cqt = ParagraphStyle("CqtStyle", fontName=font_i, fontSize=8, leading=11, alignment=1, textColor=ink)
    s_right_meta = ParagraphStyle("RightMeta", fontName=font_n, fontSize=8.5, leading=12, alignment=0, textColor=navy)
    s_field = ParagraphStyle("FieldStyle", fontName=font_n, fontSize=8.5, leading=12, textColor=ink)
    s_tbl_hdr = ParagraphStyle("TblHdr", fontName=font_b, fontSize=8, leading=10, alignment=1, textColor=navy)
    s_tbl_num = ParagraphStyle("TblNum", fontName=font_b, fontSize=7.5, leading=9.5, alignment=1, textColor=navy)
    s_cell_l = ParagraphStyle("CellL", fontName=font_n, fontSize=8.5, leading=11, textColor=ink)
    s_cell_c = ParagraphStyle("CellC", fontName=font_n, fontSize=8.5, leading=11, alignment=1, textColor=ink)
    s_cell_r = ParagraphStyle("CellR", fontName=font_n, fontSize=8.5, leading=11, alignment=2, textColor=ink)
    s_cell_rb = ParagraphStyle("CellRB", fontName=font_b, fontSize=8.5, leading=11, alignment=2, textColor=ink)
    s_sig_hdr = ParagraphStyle("SigHdr", fontName=font_b, fontSize=8.5, leading=11, alignment=1, textColor=navy)
    s_sig_sub = ParagraphStyle("SigSub", fontName=font_i, fontSize=8, leading=10, alignment=1, textColor=navy)

    story: List = []

    # Top disclaimer line (explicitly non-legal synthetic test document)
    story.append(
        Paragraph(
            "DỮ LIỆU GIẢ LẬP — MẪU HÓA ĐƠN ĐIỆN TỬ XĂNG DẦU PHỤC VỤ KIỂM THỬ PHẦN MỀM (KHÔNG CÓ GIÁ TRỊ PHÁP LÝ)",
            s_top_notice,
        )
    )
    story.append(Spacer(1, 4))

    # Build inner bordered blocks stacked inside one outer framed table (matching Vietnam e-invoice box layout)
    # 1. Title & Invoice Serial Header
    logo_box = Paragraph(
        f"<font color='#1D4ED8'><b>MẪU TEST</b></font><br/><font size='7' color='#475569'>EcoStream<br/>Tháng {month:02d}/{year}</font>",
        ParagraphStyle("LogoBox", fontName=font_b, fontSize=9, leading=11, alignment=1),
    )
    center_title = [
        Paragraph("HÓA ĐƠN GIÁ TRỊ GIA TĂNG", s_title),
        Paragraph("CHỨNG TỪ XUẤT BÁN XĂNG DẦU (GIẢ LẬP)", s_subtitle),
        Spacer(1, 3),
        Paragraph(
            f"<font color='#1D4ED8'>Ngày</font> <b>{invoice_day:02d}</b> &nbsp; "
            f"<font color='#1D4ED8'>tháng</font> <b>{month:02d}</b> &nbsp; "
            f"<font color='#1D4ED8'>năm</font> <b>{year}</b>",
            s_date,
        ),
        Spacer(1, 2),
        Paragraph(f"<font color='#1D4ED8'>Mã của cơ quan thuế (mẫu):</font> <b>{cqt_code}</b>", s_cqt),
    ]
    right_meta = Paragraph(
        f"Ký hiệu: <b>{serial_code}</b><br/>"
        f"Số: <font color='#DC2626' size='12'><b>{invoice_no}</b></font>",
        s_right_meta,
    )

    t_title_block = Table(
        [[logo_box, center_title, right_meta]],
        colWidths=[75, 315, 135],
    )
    t_title_block.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (0, 0), 0.5, grid_line),
        ("BACKGROUND", (0, 0), (0, 0), soft_tint),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))

    # 2. Seller block
    seller_para = Paragraph(
        f"<font color='#1D4ED8'>Đơn vị bán hàng (Seller):</font> <b>{seller_name}</b><br/>"
        f"<font color='#1D4ED8'>Địa chỉ (Address):</font> {seller_address}<br/>"
        f"<font color='#1D4ED8'>Mã số thuế (Code):</font> <b>{seller_tax_id}</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; "
        f"<font color='#1D4ED8'>Điện thoại (Telephone):</font> {seller_phone}<br/>"
        f"<font color='#1D4ED8'>Tài khoản:</font> DEMO-ACC-000000",
        s_field,
    )
    t_seller = Table([[seller_para]], colWidths=[525])
    t_seller.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 0.75, border_blue),
        ("LINEBELOW", (0, 0), (-1, -1), 0.75, border_blue),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))

    # 3. Buyer block
    buyer_para = Paragraph(
        f"<font color='#1D4ED8'>Họ và tên khách (Name):</font> Cán bộ phụ trách vật tư (Mẫu)<br/>"
        f"<font color='#1D4ED8'>Đơn vị mua hàng (Buyer):</font> <b>{buyer_name}</b><br/>"
        f"<font color='#1D4ED8'>Địa chỉ (Address):</font> {buyer_address}<br/>"
        f"<font color='#1D4ED8'>Mã số thuế (Code):</font> <b>{buyer_tax_id}</b><br/>"
        f"<font color='#1D4ED8'>HTTT (Mode of payment):</font> {payment_mode} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; "
        f"<font color='#1D4ED8'>Số tài khoản (Account No):</font> 000000000000",
        s_field,
    )
    t_buyer = Table([[buyer_para]], colWidths=[525])
    t_buyer.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.75, border_blue),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))

    # 4. Fuel line-items table (exact 6 columns from reference form)
    item_rows = [
        [
            Paragraph("STT<br/>(No)", s_tbl_hdr),
            Paragraph("DIỄN GIẢI<br/>(Description)", s_tbl_hdr),
            Paragraph("Đơn vị tính<br/>(Unit)", s_tbl_hdr),
            Paragraph("Số lượng<br/>(Quantity)", s_tbl_hdr),
            Paragraph("Đơn giá<br/>(Unit price)", s_tbl_hdr),
            Paragraph("Thành tiền<br/>(Amount)", s_tbl_hdr),
        ],
        [
            Paragraph("1", s_tbl_num),
            Paragraph("2", s_tbl_num),
            Paragraph("3", s_tbl_num),
            Paragraph("4", s_tbl_num),
            Paragraph("5", s_tbl_num),
            Paragraph("6=4x5", s_tbl_num),
        ],
    ]

    subtotal = 0
    for idx, item in enumerate(items, 1):
        qty = float(item["qty"])
        price = float(item["price"])
        amount = int(round(qty * price))
        subtotal += amount
        item_rows.append([
            Paragraph(str(idx), s_cell_c),
            Paragraph(item["name"], s_cell_l),
            Paragraph(item["unit"], s_cell_c),
            Paragraph(format_vn_number(qty, 2), s_cell_r),
            Paragraph(format_vn_number(price, 0), s_cell_r),
            Paragraph(format_vn_number(amount, 0), s_cell_r),
        ])

    # Pad to 5 item rows like standard Vietnamese fuel invoice grid
    while len(item_rows) < 7:
        item_rows.append([Paragraph("", s_cell_c) for _ in range(6)])

    t_items = Table(item_rows, colWidths=[35, 225, 65, 65, 65, 70], rowHeights=[28, 15] + [20] * (len(item_rows) - 2))
    t_items.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 1), soft_tint),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, border_blue),
        ("LINEBELOW", (0, 1), (-1, 1), 0.75, border_blue),
        ("LINEBEFORE", (1, 0), (-1, -1), 0.5, border_blue),
        ("LINEBELOW", (0, 2), (-1, -2), 0.4, grid_line),
        ("LINEBELOW", (0, -1), (-1, -1), 0.75, border_blue),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))

    # 5. Totals & VAT breakdown
    vat_rate = 10
    vat_amount = int(round(subtotal * vat_rate / 100.0))
    total_payment = subtotal + vat_amount
    words = number_to_vietnamese_words(total_payment)

    totals_rows = [
        [
            Paragraph("", s_field),
            Paragraph("<font color='#1D4ED8'>Cộng (Sub-total):</font>", s_field),
            Paragraph(f"<b>{format_vn_number(subtotal, 0)}</b>", s_cell_r),
        ],
        [
            Paragraph(f"<font color='#1D4ED8'>Thuế suất GTGT (VAT rate):</font> &nbsp;&nbsp;&nbsp; <b>{vat_rate}%</b>", s_field),
            Paragraph("<font color='#1D4ED8'>Tiền thuế GTGT (VAT):</font>", s_field),
            Paragraph(f"<b>{format_vn_number(vat_amount, 0)}</b>", s_cell_r),
        ],
        [
            Paragraph("", s_field),
            Paragraph("<font color='#1D4ED8'>Tổng cộng tiền thanh toán (Total):</font>", s_field),
            Paragraph(f"<b>{format_vn_number(total_payment, 0)}</b>", s_cell_rb),
        ],
        [
            Paragraph(f"<font color='#1D4ED8'>Số tiền viết bằng chữ (Total amount in words):</font> {words}.", s_field),
            Paragraph("", s_field),
            Paragraph("", s_field),
        ],
    ]
    t_totals = Table(totals_rows, colWidths=[260, 175, 90])
    t_totals.setStyle(TableStyle([
        ("SPAN", (0, 3), (2, 3)),
        ("LINEBELOW", (0, -1), (-1, -1), 0.75, border_blue),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))

    # 6. Signature & Demo Signature Box
    sig_stamp = Paragraph(
        "<font color='#DC2626'><b>[MẪU CHỮ KÝ SỐ GIẢ LẬP]</b><br/>"
        f"Ký bởi: {seller_name}<br/>"
        f"Ngày ký: {invoice_day:02d}/{month:02d}/{year}<br/>"
        "(Không có giá trị pháp lý)</font>",
        ParagraphStyle("Stamp", fontName=font_n, fontSize=7, leading=9.5, alignment=0),
    )
    t_stamp_inner = Table([[sig_stamp]], colWidths=[150])
    t_stamp_inner.setStyle(TableStyle([
        ("BOX", (0, 0), (0, 0), 0.75, ink),
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#FEF2F2")),
        ("TOPPADDING", (0, 0), (0, 0), 4),
        ("BOTTOMPADDING", (0, 0), (0, 0), 4),
        ("LEFTPADDING", (0, 0), (0, 0), 6),
        ("RIGHTPADDING", (0, 0), (0, 0), 6),
    ]))

    sig_table = Table(
        [
            [
                Paragraph("<b>Người mua hàng (Customer)</b>", s_sig_hdr),
                Paragraph("<b>Người bán hàng (Cashier)</b>", s_sig_hdr),
                Paragraph("<b>Đơn vị bán hàng (Seller)</b>", s_sig_hdr),
            ],
            [
                Paragraph("(Ký, ghi rõ họ tên)", s_sig_sub),
                Paragraph("(Ký, ghi rõ họ tên)", s_sig_sub),
                Paragraph("(Ký, đóng dấu, ghi rõ họ tên)", s_sig_sub),
            ],
            [
                Paragraph("", s_cell_c),
                Paragraph("", s_cell_c),
                t_stamp_inner,
            ],
        ],
        colWidths=[165, 170, 190],
    )
    sig_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    # Outer double-framed box wrapping sections 1..6
    outer_frame = Table(
        [[t_title_block], [t_seller], [t_buyer], [t_items], [t_totals], [sig_table]],
        colWidths=[525],
    )
    outer_frame.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1.6, border_blue),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    story.append(outer_frame)
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            f"<i>Kỳ dữ liệu: Tháng {month:02d}/{year} · Chứng từ kiểm thử EcoStream (Scope 1.1 & 1.2) · Không thay thế hóa đơn tài chính thật.</i>",
            ParagraphStyle("BottomNote", fontName=font_i, fontSize=7, leading=9, alignment=1, textColor=muted),
        )
    )
    return story


def generate_annual_fuel_pdf(
    output_path: str | Path,
    year: int = 2026,
    skip_month: Optional[int] = None,
) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        rightMargin=35,
        leftMargin=35,
        topMargin=24,
        bottomMargin=24,
    )
    story: List = []
    months = [m for m in range(1, 13) if m != skip_month]
    for idx, m in enumerate(months):
        story.extend(build_fuel_invoice_story(month=m, year=year))
        if idx < len(months) - 1:
            story.append(PageBreak())
    doc.build(story)
    return out


def generate_12_monthly_fuel_pdfs(output_dir: str | Path, year: int = 2026) -> List[Path]:
    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []
    for m in range(1, 13):
        out = folder / f"hoa_don_xang_dau_thang_{m:02d}_{year}.pdf"
        doc = SimpleDocTemplate(
            str(out),
            pagesize=A4,
            rightMargin=35,
            leftMargin=35,
            topMargin=24,
            bottomMargin=24,
        )
        doc.build(build_fuel_invoice_story(month=m, year=year))
        paths.append(out)
    return paths


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic 12-month Vietnamese Fuel VAT E-Invoice PDFs.")
    parser.add_argument("--out-dir", type=str, default="data/demo_fuel_2026_12months", help="Directory for 12 monthly PDFs")
    parser.add_argument("--bundle-out", type=str, default="data/demo_fuel_2026_12months/hoa_don_xang_dau_12_thang_2026.pdf", help="Path for consolidated 12-page PDF")
    parser.add_argument("--year", type=int, default=2026, help="Invoice year")
    args = parser.parse_args()

    monthly = generate_12_monthly_fuel_pdfs(args.out_dir, year=args.year)
    bundle = generate_annual_fuel_pdf(args.bundle_out, year=args.year)
    print(f"Generated {len(monthly)} monthly fuel PDFs in {args.out_dir}")
    print(f"Generated 12-month consolidated fuel PDF: {bundle}")
