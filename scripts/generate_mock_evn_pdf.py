#!/usr/bin/env python3
"""
Generate official-standard EVN Electronic Electricity Invoice PDFs (Hóa đơn điện tử tiền điện)
strictly conforming to the latest Vietnamese Tax & E-Invoice Regulations:
- Nghị định số 123/2020/NĐ-CP & Nghị định số 70/2025/NĐ-CP ngày 20/03/2025 của Chính phủ
- Thông tư số 32/2025/TT-BTC ngày 31/05/2025 của Bộ Tài chính hướng dẫn về hóa đơn, chứng từ
- EVN Standard 3-tier Industrial Electricity Tariff & Reactive Power (kvarh / cos phi)
- Digital Certificate Signature Box & Tax Authority Verification (Mã CQT)

Used for EcoStream AI GHG Accounting, Decree 06/2022 Mẫu 02, and Scope 2 Automated Extraction Benchmark.
"""

import os
import math
import argparse
from typing import List, Dict, Optional, Tuple
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def register_vietnamese_fonts():
    """Register TrueType fonts with full Vietnamese Unicode support."""
    font_paths = [
        ("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ("DejaVuSans-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("DejaVuSans-Oblique", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"),
        ("LiberationSans", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        ("LiberationSans-Bold", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ]

    for name, path in font_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
            except Exception:
                pass


def number_to_vietnamese_words(n: int) -> str:
    """Convert integer currency into formal Vietnamese financial wording."""
    if n == 0:
        return "Không đồng"

    digits = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]

    def read_three_digits(num: int, show_zero_hundred: bool = False) -> str:
        h = num // 100
        t = (num % 100) // 10
        u = num % 10
        res = []
        if h > 0 or show_zero_hundred:
            res.append(f"{digits[h]} trăm")
        if t > 1:
            res.append(f"{digits[t]} mươi")
            if u == 1:
                res.append("mốt")
            elif u == 4:
                res.append("tư")
            elif u == 5:
                res.append("lăm")
            elif u > 0:
                res.append(digits[u])
        elif t == 1:
            res.append("mười")
            if u == 5:
                res.append("lăm")
            elif u > 0:
                res.append(digits[u])
        elif t == 0:
            if (h > 0 or show_zero_hundred) and u > 0:
                res.append(f"lẻ {digits[u]}")
            elif u > 0:
                res.append(digits[u])
        return " ".join(res)

    billions = n // 1_000_000_000
    millions = (n % 1_000_000_000) // 1_000_000
    thousands = (n % 1_000_000) // 1_000
    units = n % 1_000

    parts = []
    if billions > 0:
        parts.append(f"{read_three_digits(billions)} tỷ")
    if millions > 0:
        parts.append(f"{read_three_digits(millions, len(parts) > 0)} triệu")
    if thousands > 0:
        parts.append(f"{read_three_digits(thousands, len(parts) > 0)} nghìn")
    if units > 0:
        parts.append(f"{read_three_digits(units, len(parts) > 0)}")
    parts.append("đồng")

    sentence = " ".join(parts).strip()
    return sentence[0].upper() + sentence[1:]


def create_nd70_evn_invoice_story(
    month: int,
    year: int,
    company_name: str,
    tax_id: str,
    address: str,
    customer_id: str,
    meter_id: str,
    kwh_bt: int,
    kwh_cd: int,
    kwh_td: int,
    kvarh: Optional[int] = None,
    contract_no: str = "HĐMBĐ-2024/NTL-089",
    voltage_level: str = "Cấp điện áp Trung thế (22kV) - Sản xuất công nghiệp 3 ca",
    substation: str = "Trạm chuyên dùng 560 kVA",
    base_meter_bt: int = 142500,
    base_meter_cd: int = 48200,
    base_meter_td: int = 89100,
    base_meter_kvarh: int = 35000,
) -> List:
    """
    Constructs the exact layout of EVN Official E-Invoice conforming strictly to:
    - Nghị định số 70/2025/NĐ-CP & Nghị định số 123/2020/NĐ-CP
    - Thông tư số 32/2025/TT-BTC (Bộ Tài chính)
    """
    font_normal = "DejaVuSans" if "DejaVuSans" in pdfmetrics.getRegisteredFontNames() else "Helvetica"
    font_bold = "DejaVuSans-Bold" if "DejaVuSans-Bold" in pdfmetrics.getRegisteredFontNames() else "Helvetica-Bold"
    font_italic = "DejaVuSans-Oblique" if "DejaVuSans-Oblique" in pdfmetrics.getRegisteredFontNames() else "Helvetica-Oblique"

    # Color Palette conforming to EVN branding
    evn_blue = colors.HexColor("#003399")
    evn_dark = colors.HexColor("#0D47A1")
    header_bg = colors.HexColor("#EBF3FB")
    grid_color = colors.HexColor("#B0BEC5")
    dark_text = colors.HexColor("#1A202C")
    red_accent = colors.HexColor("#C62828")
    green_sign = colors.HexColor("#1B5E20")

    # Typography Styles
    title_main = ParagraphStyle(
        "TitleMain",
        fontName=font_bold,
        fontSize=13,
        leading=16,
        alignment=1,
        textColor=evn_dark,
    )
    title_sub = ParagraphStyle(
        "TitleSub",
        fontName=font_bold,
        fontSize=10,
        leading=13,
        alignment=1,
        textColor=evn_blue,
    )
    title_legal = ParagraphStyle(
        "TitleLegal",
        fontName=font_italic,
        fontSize=7,
        leading=9.5,
        alignment=1,
        textColor=colors.HexColor("#455A64"),
    )
    period_style = ParagraphStyle(
        "PeriodStyle",
        fontName=font_bold,
        fontSize=8.5,
        leading=11,
        alignment=1,
        textColor=dark_text,
    )
    evn_seller_hdr = ParagraphStyle(
        "SellerHdr",
        fontName=font_bold,
        fontSize=8,
        leading=11,
        textColor=evn_dark,
    )
    meta_style = ParagraphStyle(
        "MetaStyle",
        fontName=font_normal,
        fontSize=7.5,
        leading=10.5,
        alignment=2, # Right aligned
        textColor=dark_text,
    )
    cell_normal = ParagraphStyle(
        "CellNormal",
        fontName=font_normal,
        fontSize=7.5,
        leading=10,
        textColor=dark_text,
    )
    cell_bold = ParagraphStyle(
        "CellBold",
        fontName=font_bold,
        fontSize=7.5,
        leading=10,
        textColor=dark_text,
    )
    cell_center = ParagraphStyle(
        "CellCenter",
        fontName=font_normal,
        fontSize=7.5,
        leading=10,
        alignment=1,
        textColor=dark_text,
    )
    cell_center_bold = ParagraphStyle(
        "CellCenterBold",
        fontName=font_bold,
        fontSize=7.5,
        leading=10,
        alignment=1,
        textColor=dark_text,
    )
    cell_right = ParagraphStyle(
        "CellRight",
        fontName=font_normal,
        fontSize=7.5,
        leading=10,
        alignment=2,
        textColor=dark_text,
    )
    cell_right_bold = ParagraphStyle(
        "CellRightBold",
        fontName=font_bold,
        fontSize=7.5,
        leading=10,
        alignment=2,
        textColor=dark_text,
    )

    story = []

    # -------------------------------------------------------------------------
    # 1. HEADER SECTION (Seller Info & Decree 70/2025/NĐ-CP E-Invoice Metadata)
    # -------------------------------------------------------------------------
    last_day = 28 if month == 2 and year % 4 != 0 else (29 if month == 2 else (30 if month in (4,6,9,11) else 31))
    invoice_no = (month * 3141 + 48291) % 999999
    cqt_code = f"00{year%100}CQT0100100417009{invoice_no:06d}"
    lookup_code = f"EVN{year}{month:02d}{customer_id[-4:]}"

    seller_text = (
        "<b>TẬP ĐOÀN ĐIỆN LỰC VIỆT NAM</b><br/>"
        "<b>TỔNG CÔNG TY ĐIỆN LỰC TP HÀ NỘI</b><br/>"
        "<b>CÔNG TY ĐIỆN LỰC BẮC TỪ LIÊM</b><br/>"
        "<font color='#37474F'>Mã số thuế: <b>0100100417-009</b><br/>"
        "Địa chỉ: Số 2 Phố Tây Tựu, P. Minh Khai, Q. Bắc Từ Liêm, TP. Hà Nội<br/>"
        "Điện thoại CSKH: <b>1900 1288</b> | Website: cskh.evnhanoi.com.vn<br/>"
        "Tài khoản: 110000003456 tại Ngân hàng TMCP Công Thương Việt Nam</font>"
    )

    meta_text = (
        f"<b>Mẫu số (Form):</b> <font color='#0D47A1'><b>1</b></font><br/>"
        f"<b>Ký hiệu (Serial):</b> <font color='#0D47A1'><b>1C{year%100}THN</b></font><br/>"
        f"<b>Số (No.):</b> <font color='#C62828'><b>{invoice_no:08d}</b></font><br/>"
        f"<b>Ngày lập (Date):</b> {last_day:02d}/{month:02d}/{year}<br/>"
        f"<b>Mã CQT:</b> {cqt_code}<br/>"
        f"<b>Mã tra cứu:</b> <b>{lookup_code}</b>"
    )

    t_header = Table(
        [
            [Paragraph(seller_text, evn_seller_hdr), Paragraph(meta_text, meta_style)]
        ],
        colWidths=[310, 215],
    )
    t_header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 5))

    # -------------------------------------------------------------------------
    # 2. INVOICE TITLE & LEGAL CITATIONS (NĐ 70/2025/NĐ-CP & TT 32/2025/TT-BTC)
    # -------------------------------------------------------------------------
    story.append(Paragraph("HÓA ĐƠN GIÁ TRỊ GIA TĂNG", title_main))
    story.append(Paragraph("(TIỀN ĐIỆN)", title_sub))
    story.append(
        Paragraph(
            "(Bản thể hiện của hóa đơn điện tử khởi tạo theo Nghị định 123/2020/NĐ-CP, "
            "<b>Nghị định 70/2025/NĐ-CP</b> ngày 20/03/2025 và <b>Thông tư 32/2025/TT-BTC</b> ngày 31/05/2025 của Bộ Tài chính)",
            title_legal,
        )
    )
    story.append(Spacer(1, 2))
    story.append(Paragraph(f"<b>Kỳ: 1</b> (Từ ngày 01/{month:02d}/{year} đến ngày {last_day:02d}/{month:02d}/{year})", period_style))
    story.append(Spacer(1, 5))

    # -------------------------------------------------------------------------
    # 3. BUYER / CUSTOMER INFORMATION (Đơn vị sử dụng điện)
    # -------------------------------------------------------------------------
    cust_table_data = [
        [
            Paragraph("<b>Tên khách hàng:</b>", cell_normal),
            Paragraph(f"<b>{company_name}</b>", cell_bold),
        ],
        [
            Paragraph("<b>Địa chỉ sử dụng điện:</b>", cell_normal),
            Paragraph(address, cell_normal),
        ],
        [
            Paragraph("<b>Mã số thuế / Mã định danh:</b>", cell_normal),
            Paragraph(f"<b>{tax_id}</b>", cell_bold),
        ],
        [
            Paragraph("<b>Mã khách hàng (PE):</b>", cell_normal),
            Paragraph(f"<b>{customer_id}</b> &nbsp;&nbsp;|&nbsp;&nbsp; Hợp đồng: <b>{contract_no}</b>", cell_normal),
        ],
        [
            Paragraph("<b>Số công tơ / Trạm:</b>", cell_normal),
            Paragraph(f"Công tơ: <b>{meter_id}</b> &nbsp;&nbsp;|&nbsp;&nbsp; Trạm biến áp: <b>{substation}</b>", cell_normal),
        ],
        [
            Paragraph("<b>Cấp điện áp & Mục đích:</b>", cell_normal),
            Paragraph(voltage_level, cell_normal),
        ],
    ]
    t_cust = Table(cust_table_data, colWidths=[115, 410])
    t_cust.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8F9FA")),
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor("#CFD8DC")),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor("#ECEFF1")),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_cust)
    story.append(Spacer(1, 5))

    # -------------------------------------------------------------------------
    # 4. MEASUREMENT BREAKDOWN (Bảng chỉ số đo đếm & Biểu giá 3 thành phần)
    # -------------------------------------------------------------------------
    # EVN Industrial Tariff (Thông tư 09/2023/TT-BCT & Quyết định 2941/QĐ-BCT / TT 32/2025/TT-BTC)
    price_bt = 1738  # Giờ bình thường (đồng/kWh)
    price_cd = 3076  # Giờ cao điểm (đồng/kWh)
    price_td = 1100  # Giờ thấp điểm (đồng/kWh)

    old_bt = base_meter_bt + (month - 1) * kwh_bt
    new_bt = old_bt + kwh_bt
    amount_bt = kwh_bt * price_bt

    old_cd = base_meter_cd + (month - 1) * kwh_cd
    new_cd = old_cd + kwh_cd
    amount_cd = kwh_cd * price_cd

    old_td = base_meter_td + (month - 1) * kwh_td
    new_td = old_td + kwh_td
    amount_td = kwh_td * price_td

    total_kwh_active = kwh_bt + kwh_cd + kwh_td
    total_amount_active = amount_bt + amount_cd + amount_td

    # Reactive power calculation (kvarh & cos phi)
    if kvarh is None:
        kvarh = int(total_kwh_active * 0.28)

    old_kvarh = base_meter_kvarh + (month - 1) * kvarh
    new_kvarh = old_kvarh + kvarh

    cos_phi = total_kwh_active / math.sqrt(total_kwh_active**2 + kvarh**2) if total_kwh_active > 0 else 1.0
    k_penalty_rate = 0.0
    reactive_penalty_amount = 0
    if cos_phi < 0.90:
        k_penalty_rate = round((0.90 / cos_phi - 1) * 100, 2)
        reactive_penalty_amount = int(total_amount_active * (k_penalty_rate / 100.0))

    table_data = [
        # Table Header
        [
            Paragraph("<b>Bộ chỉ số (Thời gian biểu)</b>", cell_center_bold),
            Paragraph("<b>Chỉ số cũ</b>", cell_center_bold),
            Paragraph("<b>Chỉ số mới</b>", cell_center_bold),
            Paragraph("<b>HSN</b>", cell_center_bold),
            Paragraph("<b>Điện năng tiêu thụ (kWh)</b>", cell_center_bold),
            Paragraph("<b>Đơn giá (đồng)</b>", cell_center_bold),
            Paragraph("<b>Thành tiền (đồng)</b>", cell_center_bold),
        ],
        # Section I: Active Power (Ap)
        [
            Paragraph("<b>I. Điện năng tác dụng (Ap)</b>", cell_bold),
            Paragraph("", cell_center),
            Paragraph("", cell_center),
            Paragraph("", cell_center),
            Paragraph("", cell_center),
            Paragraph("", cell_center),
            Paragraph("", cell_center),
        ],
        [
            Paragraph("&nbsp;&nbsp;1. Giờ bình thường (BT)", cell_normal),
            Paragraph(f"{old_bt:n}", cell_center),
            Paragraph(f"{new_bt:n}", cell_center),
            Paragraph("1.0", cell_center),
            Paragraph(f"<b>{kwh_bt:n}</b>", cell_center),
            Paragraph(f"{price_bt:n}", cell_right),
            Paragraph(f"{amount_bt:n}", cell_right),
        ],
        [
            Paragraph("&nbsp;&nbsp;2. Giờ cao điểm (CĐ)", cell_normal),
            Paragraph(f"{old_cd:n}", cell_center),
            Paragraph(f"{new_cd:n}", cell_center),
            Paragraph("1.0", cell_center),
            Paragraph(f"<b>{kwh_cd:n}</b>", cell_center),
            Paragraph(f"{price_cd:n}", cell_right),
            Paragraph(f"{amount_cd:n}", cell_right),
        ],
        [
            Paragraph("&nbsp;&nbsp;3. Giờ thấp điểm (TĐ)", cell_normal),
            Paragraph(f"{old_td:n}", cell_center),
            Paragraph(f"{new_td:n}", cell_center),
            Paragraph("1.0", cell_center),
            Paragraph(f"<b>{kwh_td:n}</b>", cell_center),
            Paragraph(f"{price_td:n}", cell_right),
            Paragraph(f"{amount_td:n}", cell_right),
        ],
        [
            Paragraph("<b>Cộng điện năng tác dụng (Ap)</b>", cell_bold),
            Paragraph("", cell_center),
            Paragraph("", cell_center),
            Paragraph("", cell_center),
            Paragraph(f"<b>{total_kwh_active:n} kWh</b>", cell_center_bold),
            Paragraph("", cell_center),
            Paragraph(f"<b>{total_amount_active:n}</b>", cell_right_bold),
        ],
        # Section II: Reactive Power (Aq)
        [
            Paragraph("<b>II. Điện năng phản kháng (Aq)</b>", cell_bold),
            Paragraph(f"{old_kvarh:n}", cell_center),
            Paragraph(f"{new_kvarh:n}", cell_center),
            Paragraph("1.0", cell_center),
            Paragraph(f"<b>{kvarh:n} kvarh</b>", cell_center),
            Paragraph(f"cosφ = {cos_phi:.2f}", cell_center),
            Paragraph(f"{reactive_penalty_amount:n}", cell_right),
        ],
    ]

    t_measure = Table(table_data, colWidths=[130, 60, 60, 30, 85, 70, 90])
    t_measure.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), header_bg),
        ('GRID', (0, 0), (-1, -1), 0.5, grid_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#F5F5F5")),
        ('SPAN', (0, 1), (6, 1)),
        ('BACKGROUND', (0, 5), (-1, 5), colors.HexColor("#E3F2FD")),
        ('BACKGROUND', (0, 6), (-1, 6), colors.HexColor("#FAFAFA")),
    ]))
    story.append(t_measure)
    story.append(Spacer(1, 5))

    # -------------------------------------------------------------------------
    # 5. FINANCIAL SUMMARY & VAT BREAKDOWN (Cộng tiền điện & Thuế GTGT)
    # -------------------------------------------------------------------------
    subtotal_before_vat = total_amount_active + reactive_penalty_amount
    vat_rate = 8  # 8% VAT under Government Decrees on VAT Reduction
    vat_amount = int(round(subtotal_before_vat * (vat_rate / 100.0)))
    total_payment = subtotal_before_vat + vat_amount

    summary_rows = [
        [
            Paragraph("Cộng tiền điện năng tác dụng (Chưa có thuế GTGT):", cell_normal),
            Paragraph(f"<b>{total_amount_active:n} VNĐ</b>", cell_right),
        ],
        [
            Paragraph("Tiền mua công suất phản kháng (nếu có):", cell_normal),
            Paragraph(f"{reactive_penalty_amount:n} VNĐ", cell_right),
        ],
        [
            Paragraph("<b>Cộng tiền điện (Chưa có thuế GTGT):</b>", cell_bold),
            Paragraph(f"<b>{subtotal_before_vat:n} VNĐ</b>", cell_right_bold),
        ],
        [
            Paragraph(f"Thuế suất GTGT: <b>{vat_rate}%</b> &nbsp;&nbsp;|&nbsp;&nbsp; Tiền thuế GTGT:", cell_normal),
            Paragraph(f"<b>{vat_amount:n} VNĐ</b>", cell_right),
        ],
        [
            Paragraph("<b>TỔNG CỘNG TIỀN THANH TOÁN (ĐÃ CÓ THUẾ GTGT):</b>", ParagraphStyle("RedTotal", fontName=font_bold, fontSize=8.5, textColor=red_accent)),
            Paragraph(f"<b>{total_payment:n} VNĐ</b>", ParagraphStyle("RedTotalR", fontName=font_bold, fontSize=9, alignment=2, textColor=red_accent)),
        ],
    ]
    t_summary = Table(summary_rows, colWidths=[340, 185])
    t_summary.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 0.5, grid_color),
        ('LINEBELOW', (0, -1), (-1, -1), 1.2, red_accent),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 3))

    # Amount in Vietnamese words
    words = number_to_vietnamese_words(total_payment)
    story.append(Paragraph(f"<b>Số tiền viết bằng chữ:</b> <i>{words}</i>", ParagraphStyle("WordsStyle", fontName=font_italic, fontSize=7.5, leading=10, textColor=dark_text)))
    story.append(Spacer(1, 8))

    # -------------------------------------------------------------------------
    # 6. DIGITAL SIGNATURES & OFFICIAL EVN CERTIFICATE STAMP (NĐ 70/2025/NĐ-CP)
    # -------------------------------------------------------------------------
    sig_data = [
        [
            Paragraph(
                "<b>NGƯỜI MUA HÀNG</b><br/>"
                "<i>(Khách hàng ký số theo NĐ 70/2025/NĐ-CP nếu có)</i><br/><br/><br/>"
                f"<b>{company_name}</b>",
                ParagraphStyle("SigBuyer", fontName=font_normal, fontSize=7.5, leading=10, alignment=1),
            ),
            Paragraph(
                "<b>NGƯỜI BÁN HÀNG - ĐẠI DIỆN EVN</b><br/>"
                "<i>(Ký số điện tử theo Nghị định 70/2025/NĐ-CP & Thông tư 32/2025/TT-BTC)</i><br/><br/>"
                "<font color='#1B5E20'><b>[✓ CHỮ KÝ SỐ HỢP LỆ & XÁC THỰC CQT]</b><br/>"
                "<b>Ký bởi: TỔNG CÔNG TY ĐIỆN LỰC TP HÀ NỘI</b><br/>"
                f"Thời điểm ký: {last_day:02d}/{month:02d}/{year} 23:59:59<br/>"
                "Chứng thư số: CA-EVN-00100417-ND70-2026-VAL</font>",
                ParagraphStyle("SigSeller", fontName=font_normal, fontSize=7.5, leading=9.5, alignment=1),
            ),
        ]
    ]
    t_sig = Table(sig_data, colWidths=[240, 285])
    t_sig.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (1, 0), (1, 0), 0.75, colors.HexColor("#4CAF50")),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor("#F1F8E9")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_sig)
    story.append(Spacer(1, 6))

    # -------------------------------------------------------------------------
    # 7. FOOTER NOTE & OFFICIAL TAX PORTAL
    # -------------------------------------------------------------------------
    footer_note = (
        "<font color='#546E7A'><i>Tra cứu hóa đơn điện tử tại Cổng Tổng cục Thuế: <b>https://hoadondientu.gdt.gov.vn</b> "
        f"hoặc Portal CSKH: <b>https://cskh.evnhanoi.com.vn</b> với Mã tra cứu: <b>{lookup_code}</b> | "
        "(Hóa đơn điện tử có giá trị pháp lý theo Nghị định 123/2020/NĐ-CP, Nghị định 70/2025/NĐ-CP và Thông tư 32/2025/TT-BTC)</i></font>"
    )
    story.append(Paragraph(footer_note, ParagraphStyle("FooterNote", fontName=font_normal, fontSize=6.5, leading=8.5, alignment=1)))

    return story


def generate_single_evn_pdf(
    output_path: str,
    month: int = 3,
    year: int = 2026,
    company_name: str = "CÔNG TY CỔ PHẦN MAY MẶC ECOGARMENT VIỆT NAM",
    tax_id: str = "0109283746",
    address: str = "Lô CN-08, Khu Công nghiệp Nam Thăng Long, Phường Thụy Phương, Quận Bắc Từ Liêm, TP. Hà Nội",
    customer_id: str = "PD04000389201",
    meter_id: str = "EVN-NTL-560-01",
    kwh_bt: int = 22300,
    kwh_cd: int = 8450,
    kwh_td: int = 14500,
):
    """Generate a single month official EVN PDF invoice under Decree 70/2025 & Circular 32/2025."""
    register_vietnamese_fonts()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=22,
        bottomMargin=22,
    )
    story = create_nd70_evn_invoice_story(
        month=month,
        year=year,
        company_name=company_name,
        tax_id=tax_id,
        address=address,
        customer_id=customer_id,
        meter_id=meter_id,
        kwh_bt=kwh_bt,
        kwh_cd=kwh_cd,
        kwh_td=kwh_td,
    )
    doc.build(story)
    print(f"✓ Successfully generated official NĐ 70/2025 & TT 32/2025 EVN invoice PDF: {output_path}")


def generate_annual_evn_bundle_pdf(
    output_path: str,
    year: int = 2026,
    skip_month: Optional[int] = 7,  # Default skip month 7 to test seasonal linear interpolation
    company_name: str = "CÔNG TY CỔ PHẦN MAY MẶC ECOGARMENT VIỆT NAM",
    tax_id: str = "0109283746",
    address: str = "Lô CN-08, Khu Công nghiệp Nam Thăng Long, Phường Thụy Phương, Quận Bắc Từ Liêm, TP. Hà Nội",
    customer_id: str = "PD04000389201",
    meter_id: str = "EVN-NTL-560-01",
):
    """Generate a multi-page PDF containing 12 monthly invoices conforming to Decree 70/2025 & Circular 32/2025."""
    register_vietnamese_fonts()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=22,
        bottomMargin=22,
    )

    monthly_profiles = {
        1: (20500, 7800, 13200),
        2: (17200, 6400, 11000),  # Lunar New Year lower
        3: (22300, 8450, 14500),
        4: (23100, 8900, 15000),
        5: (26500, 10200, 17800), # Summer cooling starts
        6: (28000, 11000, 18500), # Peak summer
        7: (29200, 11500, 19200), # Missing month candidate
        8: (28500, 11100, 18900),
        9: (25400, 9800, 16500),
        10: (24000, 9200, 15800),
        11: (23500, 9000, 15400),
        12: (24800, 9600, 16200), # Year-end delivery surge
    }

    full_story = []
    months_included = []

    for m in range(1, 13):
        if skip_month is not None and m == skip_month:
            print(f"ℹ Skipping month {m:02d}/{year} in bundle to test AI seasonal linear interpolation.")
            continue

        months_included.append(m)
        k_bt, k_cd, k_td = monthly_profiles[m]
        page_story = create_nd70_evn_invoice_story(
            month=m,
            year=year,
            company_name=company_name,
            tax_id=tax_id,
            address=address,
            customer_id=customer_id,
            meter_id=meter_id,
            kwh_bt=k_bt,
            kwh_cd=k_cd,
            kwh_td=k_td,
        )
        full_story.extend(page_story)
        if m != 12:
            full_story.append(PageBreak())

    doc.build(full_story)
    print(f"✓ Successfully generated annual NĐ 70/2025 & TT 32/2025 EVN invoice bundle ({len(months_included)} pages) PDF: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate official NĐ 70/2025 & TT 32/2025 EVN e-invoice PDFs for EcoStream GHG PoC.")
    parser.add_argument("--out", type=str, default="data/samples/sample_evn_bill.pdf", help="Output PDF file path")
    parser.add_argument("--mode", choices=["single", "annual"], default="single", help="Generate single bill or 12-month annual bundle")
    parser.add_argument("--skip-month", type=int, default=None, help="Month to skip (1-12) to test seasonal interpolation")
    parser.add_argument("--month", type=int, default=3, help="Month for single bill mode (1-12)")
    parser.add_argument("--year", type=int, default=2026, help="Invoice year")
    parser.add_argument("--company", type=str, default="CÔNG TY CỔ PHẦN MAY MẶC ECOGARMENT VIỆT NAM", help="Customer company name")
    parser.add_argument("--tax-id", type=str, default="0109283746", help="Customer tax identification number")

    args = parser.parse_args()

    if args.mode == "single":
        generate_single_evn_pdf(
            output_path=args.out,
            month=args.month,
            year=args.year,
            company_name=args.company,
            tax_id=args.tax_id,
        )
    else:
        generate_annual_evn_bundle_pdf(
            output_path=args.out,
            year=args.year,
            skip_month=args.skip_month,
            company_name=args.company,
            tax_id=args.tax_id,
        )
