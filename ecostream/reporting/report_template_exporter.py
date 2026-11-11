"""Write a clean facility report using the supplied DOCX's page setup and styles.

The supplied example contains real-looking names, addresses, and 2024 numbers. Its
body is removed deliberately so no example record can leak into a new report.
"""
from __future__ import annotations

from pathlib import Path
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from ecostream.ingestion.survey_workbook import TEMPLATES
from ecostream.models.results import AuditReport

REPORT_NAME = "2.-ND06._GHGs-Report-NS2PC_Final_VN (1).docx"


def export_report(report: AuditReport, target: str, evidence_files: list[dict], warnings: list[str]) -> None:
    original = Document(TEMPLATES / REPORT_NAME)
    # Start a clean package: deleting only the example body leaves embedded photos,
    # metadata and other unreferenced sample parts inside the DOCX archive.
    doc = Document()
    for src, dst in zip(original.sections, doc.sections):
        for attribute in ("page_width", "page_height", "top_margin", "bottom_margin", "left_margin", "right_margin"):
            setattr(dst, attribute, getattr(src, attribute))
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(11)
    s = report.summary
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.add_run("BÁO CÁO KẾT QUẢ KIỂM KÊ KHÍ NHÀ KÍNH").bold = True
    subtitle = doc.add_paragraph(f"Cơ sở: {s.facility_location} — Năm {s.reporting_period}")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f"Đơn vị: {s.company_name}")
    doc.add_paragraph("BẢN DỰ THẢO ĐỂ ĐỐI SOÁT — không thay thế hồ sơ kiểm kê được thẩm tra/duyệt.")
    doc.add_heading("1. Phạm vi và nguồn dữ liệu", level=1)
    doc.add_paragraph("Báo cáo giới hạn trong các nguồn đốt nhiên liệu có hệ số phù hợp và điện mua từ lưới (Scope 1 và Scope 2) đã có trong biểu khảo sát. Không coi các nguồn để trống là bằng không.")
    doc.add_paragraph("Dữ liệu đầu vào: biểu khảo sát được tạo từ chứng từ do người dùng cung cấp hoặc biểu khảo sát do người dùng hiệu chỉnh. Cần đối chiếu chứng từ gốc trước khi sử dụng chính thức.")
    doc.add_heading("2. Phương pháp và kết quả", level=1)
    doc.add_paragraph("Mỗi hoạt động được tính theo E (tCO₂e) = Lượng hoạt động × EF (kgCO₂e/đơn vị) / 1000. Hệ số, đơn vị và nguồn được ghi trong bảng. Workbook tham chiếu sử dụng mô hình tính riêng theo nhiệt trị và từng khí; tổng của nó cần rà soát độc lập trước khi nộp.")
    doc.add_paragraph(f"Scope 1: {s.scope_1_tonnes:,.3f} tCO₂e; Scope 2: {s.scope_2_tonnes:,.3f} tCO₂e; Tổng các nguồn đã tính: {s.total_co2e_tonnes:,.3f} tCO₂e.")
    doc.add_paragraph(f"Chỉ số chất lượng dữ liệu nội bộ EcoStream: {s.reliability.overall_confidence_score:.1f}%. Khoảng bất định mô hình: {s.total_uncertainty_min_tonnes:,.3f}–{s.total_uncertainty_max_tonnes:,.3f} tCO₂e (không công bố là khoảng tin cậy 95%).")
    table = doc.add_table(rows=1, cols=6)
    if "Table Grid" in [style.name for style in doc.styles]:
        table.style = "Table Grid"
    for i, h in enumerate(("Nguồn", "Scope", "Lượng", "Đơn vị", "EF kgCO₂e/đơn vị", "tCO₂e")):
        table.rows[0].cells[i].text = h
    for calc in report.calculations:
        cells = table.add_row().cells
        for i, value in enumerate((calc.description, calc.scope.value, f"{calc.activity_value:,.3f}", calc.activity_unit, f"{calc.emission_factor_value:g}", f"{calc.co2e_tonnes:,.4f}")):
            cells[i].text = value
    doc.add_heading("3. Chứng từ và kiểm soát chất lượng", level=1)
    for entry in evidence_files:
        doc.add_paragraph(f"• {entry['filename']}: {entry['status']} — {entry['records']} dòng đã dùng.")
    for warning in warnings:
        doc.add_paragraph(f"Cần rà soát: {warning}")
    if not warnings:
        doc.add_paragraph("Không có cảnh báo bóc tách; vẫn cần rà soát đầy đủ chứng từ nguồn.")
    doc.add_heading("4. Giới hạn và báo cáo giảm nhẹ", level=1)
    for source in s.uncalculated_sources:
        doc.add_paragraph(f"Chưa tính: {source}")
    if report.mitigation_summary:
        doc.add_paragraph("Kết quả giảm nhẹ được tính từ PTCS và PT đã xác minh theo GPT = PTCS − PT.")
        for measure in report.mitigation_summary.measures:
            doc.add_paragraph(f"{measure.measure_name}: {measure.emission_reduction_gpt:,.3f} tCO₂e")
    else:
        doc.add_paragraph("Chưa đủ PTCS, PT, phương pháp giám sát và minh chứng theo tài liệu phạm vi công việc để lập chương kết quả giảm nhẹ. Danh sách biện pháp hoặc chi phí đơn lẻ không đủ để xác định GPT/hạn ngạch.")
    doc.save(target)
