"""Create explicitly fictional multi-format evidence for the survey-first demo.

Run from the project root: python scripts/generate_survey_demo.py
All files are pedagogical samples, NOT invoices or official records.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from docx import Document
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "demo_full_2026"
NOTICE = "DU LIEU GIA LAP - KHONG CO GIA TRI PHAP LY"


def generate(output_dir: Path = OUT) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated = []

    # Separate streams, so none of the inputs repeats a real-world activity.
    fuel = output_dir / "fuel_stationary.xlsx"
    book = Workbook()
    sheet = book.active
    sheet.title = "FuelStationary"
    sheet.append([f"Ngày chứng từ ({NOTICE})", "Nhiên liệu", "Số lượng", "Đơn vị", "Mục đích", "Ghi chú"])
    for month in range(1, 13):
        sheet.append([f"2026-{month:02d}-12", "Dầu Diesel DO", 1000 + month * 10, "Lít", "Máy phát điện", f"DEMO-DO-{month:02d}"])
        sheet.append([f"2026-{month:02d}-13", "Than bitum", 2000 + month * 20, "kg", "Lò hơi", f"DEMO-COAL-{month:02d}"])
        sheet.append([f"2026-{month:02d}-14", "LPG", 100 + month, "kg", "Bếp công nghiệp", f"DEMO-LPG-{month:02d}"])
    book.save(fuel)
    generated.append(fuel)

    mobile = output_dir / "fuel_mobile.docx"
    doc = Document()
    doc.add_heading("Sổ tiêu thụ nhiên liệu mẫu — DỮ LIỆU GIẢ LẬP — KHÔNG CÓ GIÁ TRỊ PHÁP LÝ", 0)
    doc.add_paragraph("Không phải hóa đơn hoặc chứng từ thật.")
    table = doc.add_table(rows=1, cols=6)
    for cell, text in zip(table.rows[0].cells, ["Ngày", "Nhiên liệu", "Số lượng", "Đơn vị", "Mục đích", "Mã demo"]):
        cell.text = text
    for month in range(1, 13):
        for kind, qty in [("Xăng RON 95", 280 + month * 2), ("Dầu Diesel DO", 420 + month * 3)]:
            for cell, text in zip(table.add_row().cells, [f"2026-{month:02d}-16", kind, str(qty), "Lít", "Đội xe vận tải", f"DEMO-MOBILE-{month:02d}"]):
                cell.text = text
    doc.save(mobile)
    generated.append(mobile)

    electricity = output_dir / "electricity_months_02_12.csv"
    with electricity.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow([f"Kỳ hóa đơn (Tháng) — {NOTICE}", "Công tơ demo", "Sản lượng điện tiêu thụ (kWh)"])
        for month in range(2, 13):
            writer.writerow([f"Tháng {month:02d}/2026", "DEMO-METER-01", 30000 + 500 * month])
    generated.append(electricity)

    pdf = output_dir / "electricity_month_01.pdf"
    canvas = Canvas(str(pdf), pagesize=A4)
    fonts = ["/System/Library/Fonts/Supplemental/Arial.ttf", "C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]
    font = next((p for p in fonts if Path(p).exists()), None)
    if font:
        pdfmetrics.registerFont(TTFont("DemoFont", font))
    canvas.setFont("DemoFont" if font else "Helvetica", 12)
    for i, line in enumerate([
        "DỮ LIỆU GIẢ LẬP - KHÔNG CÓ GIÁ TRỊ PHÁP LÝ",
        "BẢNG ĐỌC CÔNG TƠ GIẢ LẬP (TIỀN ĐIỆN) - KHÔNG PHẢI HÓA ĐƠN",
        "Số (No.): DEMO-2026-01",
        "Kỳ: 1 (Từ ngày 01/01/2026 đến ngày 31/01/2026)",
        "Cộng điện năng tác dụng", "(Ap)", "30500 kWh",
        "Chỉ dùng để thử phần mềm, không dùng thanh toán hay kê khai.",
    ]):
        canvas.drawString(42, 790 - 35 * i, line)
    canvas.save()
    generated.append(pdf)

    manifest = output_dir / "README.txt"
    manifest.write_text(
        "DỮ LIỆU GIẢ LẬP / KHÔNG CÓ GIÁ TRỊ PHÁP LÝ\n"
        "Tải đồng thời bốn tệp .xlsx .docx .csv .pdf vào EcoStream, kỳ 2026.\n"
        "Đây là bộ chứng từ DEMO nhiên liệu cố định/di động và 12 tháng điện mua.\n"
        "Các mục môi chất lạnh, quá trình công nghiệp, nước thải, khai khoáng, hơi mua và giảm nhẹ CHƯA được tính; không điền bằng số 0.\n"
        "File PDF chỉ là bảng đọc công tơ giả lập, không phải hóa đơn EVN.\n"
        "Đối chiếu khảo sát: 1.1!F8=1010 L, 1.1!F5=2020 kg, 1.2!F4=282 L; 2.1!E3=30500 và E9=33500 kWh.\n"
        "Đối chiếu kiểm kê: S2-Electricity Consumption!C7=30500 và C13=33500 kWh.\n"
        "Tổng điện mua 12 tháng: 399000 kWh. Mẫu kiểm kê và EcoStream dùng phương pháp khác nhau; không coi các tổng phát thải là đã khớp.\n"
        + json.dumps({p.name: p.stat().st_size for p in generated}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return generated


if __name__ == "__main__":
    for path in generate():
        print(path)
