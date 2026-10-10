"""Export engine generating audit-ready Markdown, standalone HTML, DOCX, and PDF carbon disclosures."""

import io
import os
from datetime import datetime
from typing import List, Optional

from ecostream.models.results import AuditReport, SMEInventorySummary, CarbonCalculation
from ecostream.models.mitigation import MitigationSummary
from ecostream.models.state import QueryLogEntry, AssumptionLogEntry
from ecostream.reporting.templates import RegulatoryTemplates


class ReportExporter:
    """Exports structured audit reports with full evidence lineage and Vietnamese regulatory templates."""

    

    

    @classmethod
    def to_docx(cls, report: AuditReport) -> bytes:
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_TABLE_ALIGNMENT
        import io

        doc = Document()
        s = report.summary
        rel = s.reliability

        # Page setup
        for section in doc.sections:
            section.top_margin = Inches(0.8)
            section.bottom_margin = Inches(0.8)
            section.left_margin = Inches(0.8)
            section.right_margin = Inches(0.8)

        # Style defaults
        style = doc.styles['Normal']
        style.font.name = 'Times New Roman'
        style.font.size = Pt(12)

        # Top Center
        p1 = doc.add_paragraph()
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p1.add_run(f"CÔNG TY {s.company_name.upper()}")
        run.bold = True
        p1.add_run("\n--------------***--------------")

        # Title
        p2 = doc.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r2 = p2.add_run(f"\nBÁO CÁO\nKẾT QUẢ KIỂM KÊ KHÍ NHÀ KÍNH CHO NĂM {s.reporting_period}")
        r2.bold = True
        r2.font.size = Pt(14)
        
        p3 = doc.add_paragraph()
        p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r3 = p3.add_run(f"của cơ sở “{s.facility_location}”")
        r3.italic = True
        doc.add_paragraph()

        # Acronyms
        doc.add_heading("DANH MỤC CÁC CHỮ VIẾT TẮT", level=2)
        tbl_acr = doc.add_table(rows=5, cols=2)
        acronyms = [
            ("BĐKH", "Biến đổi khí hậu"),
            ("EF", "Hệ số phát thải (Emission Factor)"),
            ("GHG", "Khí nhà kính"),
            ("GWP", "Tiềm năng nóng lên toàn cầu"),
            ("IPCC", "Ban liên Chính phủ về biến đổi khí hậu"),
        ]
        for i, (k, v) in enumerate(acronyms):
            tbl_acr.cell(i, 0).text = k
            tbl_acr.cell(i, 1).text = v
        doc.add_paragraph()

        # TOC (Static mock)
        doc.add_heading("MỤC LỤC", level=2)
        doc.add_paragraph("I. Thông tin của cơ sở phải thực hiện kiểm kê khí nhà kính")
        doc.add_paragraph("II. Thông tin về hoạt động sản xuất kinh doanh và số liệu hoạt động")
        doc.add_paragraph("III. Kết quả thực hiện kiểm kê phát thải khí nhà kính")
        doc.add_paragraph("IV. Kết luận và kiến nghị\n")

        # I
        p4 = doc.add_paragraph()
        r4 = p4.add_run("I. Thông tin của cơ sở phải thực hiện kiểm kê khí nhà kính")
        r4.bold = True

        doc.add_paragraph("1. Tên cơ sở, địa chỉ\n"
                         f"- Tên doanh nghiệp: {s.company_name}\n"
                         f"- Cơ sở: {s.facility_location}\n"
                         f"- Năm kiểm kê: {s.reporting_period}")
        
        doc.add_paragraph("2. Lĩnh vực hoạt động\n"
                         f"Lĩnh vực: {s.industry_sector}")

        # II
        p5 = doc.add_paragraph()
        r5 = p5.add_run("II. Thông tin về hoạt động sản xuất kinh doanh và số liệu hoạt động của cơ sở")
        r5.bold = True

        doc.add_paragraph(f"1. Ranh giới và phạm vi hoạt động\nRanh giới kiểm kê bao gồm toàn bộ hoạt động bên trong ranh giới cơ sở {s.facility_location}. Các nguồn phát thải được kiểm kê trong kỳ này bao gồm Phạm vi 1 (Phát thải trực tiếp từ đốt nhiên liệu) và Phạm vi 2 (Phát thải gián tiếp từ điện tiêu thụ).")
        
        doc.add_paragraph("Lưu ý: Các nguồn sau chưa được đưa vào phạm vi tính toán (loại trừ theo giới hạn hệ thống):\n"
                         "- Khí rò rỉ môi chất lạnh (F-gases) từ hệ thống điều hòa/làm mát\n"
                         "- Nước thải công nghiệp và sinh hoạt chưa được xử lý\n"
                         "- Chất thải rắn chôn lấp (Scope 1/3 tùy ranh giới)\n"
                         "- Lượng nhiên liệu sử dụng cho phương tiện vận tải bên thứ ba (Scope 3 - không đưa vào tính toán giới hạn đợt 1)\n"
                         "- Phát thải từ chuỗi cung ứng nguyên vật liệu (Scope 3)")

        # III
        p6 = doc.add_paragraph()
        r6 = p6.add_run("III. Kết quả thực hiện kiểm kê phát thải khí nhà kính")
        r6.bold = True

        doc.add_paragraph("1. Phương pháp luận\nKiểm kê được thực hiện dựa trên hướng dẫn của IPCC và các quy định của Bộ TN&MT (NĐ 06/2022/NĐ-CP). Phương pháp chung: PT = AD x EF")

        doc.add_paragraph("2. Số liệu hoạt động và hệ số phát thải")
        
        # Table of AD and EF
        tbl_calcs = doc.add_table(rows=1, cols=4, style="Table Grid")
        hdr_cells = tbl_calcs.rows[0].cells
        hdr_cells[0].text = "STT"
        hdr_cells[1].text = "Hoạt động / Nguồn"
        hdr_cells[2].text = "Lượng (AD)"
        hdr_cells[3].text = "Hệ số phát thải (EF)"
        for cell in hdr_cells:
            cell.paragraphs[0].runs[0].bold = True

        for i, c in enumerate(report.calculations):
            row = tbl_calcs.add_row().cells
            row[0].text = str(i + 1)
            row[1].text = f"[{c.scope}] {c.description}"
            row[2].text = f"{c.activity_value:,.2f} {c.activity_unit}"
            row[3].text = str(c.emission_factor_value)
        doc.add_paragraph()

        doc.add_paragraph("3. Tổng hợp Kết quả phát thải KNK")
        doc.add_paragraph(f"Tổng phát thải ròng toàn cơ sở: {s.total_co2e_tonnes:.3f} tCO2e\n- Scope 1 (Trực tiếp): {s.scope_1_tonnes:.3f} tCO2e\n- Scope 2 (Gián tiếp): {s.scope_2_tonnes:.3f} tCO2e\n- Khoảng tin cậy: [{s.total_uncertainty_min_tonnes:.3f} - {s.total_uncertainty_max_tonnes:.3f}] tCO2e")

        # IV
        p7 = doc.add_paragraph()
        r7 = p7.add_run("IV. Kết luận và kiến nghị")
        r7.bold = True

        doc.add_paragraph(f"Hệ thống đạt điểm tin cậy là {rel.overall_confidence_score:.1f}%. Dữ liệu đã được kiểm soát bởi EcoStream AI.")
        
        for idx, rec in enumerate(s.recommendations):
            doc.add_paragraph(f"Kiến nghị {rec.priority}: {rec.title} - {rec.action_required}")

        doc.add_paragraph("\n\n")
        sig_p = doc.add_paragraph()
        sig_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        sig_r = sig_p.add_run("ĐẠI DIỆN CƠ SỞ\n\n(Ký và đóng dấu)")
        sig_r.bold = True

        # Save
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.read()
    
    @classmethod
    def to_pdf(cls, report: AuditReport) -> bytes:
        import io
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import os

        font_name = "Helvetica"
        font_name_bold = "Helvetica-Bold"
        for font_candidate in [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]:
            if os.path.exists(font_candidate):
                try:
                    pdfmetrics.registerFont(TTFont("CustomSans", font_candidate))
                    font_name = "CustomSans"
                    font_name_bold = "CustomSans"
                    break
                except Exception:
                    pass

        s = report.summary
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        elements = []

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("TitleStyle", fontName=font_name_bold, fontSize=14, alignment=1)
        sub_title = ParagraphStyle("SubTitle", fontName=font_name_bold, fontSize=12, alignment=1)
        normal = ParagraphStyle("NormalText", fontName=font_name, fontSize=11, leading=14)
        bold_text = ParagraphStyle("BoldText", fontName=font_name_bold, fontSize=11, leading=14)

        elements.append(Paragraph(f"CÔNG TY {s.company_name.upper()}", title_style))
        elements.append(Paragraph("--------------***--------------", sub_title))
        elements.append(Spacer(1, 15))
        
        elements.append(Paragraph("BÁO CÁO", title_style))
        elements.append(Paragraph(f"KẾT QUẢ KIỂM KÊ KHÍ NHÀ KÍNH CHO NĂM {s.reporting_period}", title_style))
        elements.append(Paragraph(f"của cơ sở “{s.facility_location}”", sub_title))
        elements.append(Spacer(1, 20))

        elements.append(Paragraph("DANH MỤC CÁC CHỮ VIẾT TẮT", bold_text))
        elements.append(Spacer(1, 5))
        acr_data = [
            ["BĐKH", "Biến đổi khí hậu"],
            ["EF", "Hệ số phát thải (Emission Factor)"],
            ["GHG", "Khí nhà kính"],
            ["GWP", "Tiềm năng nóng lên toàn cầu"],
            ["IPCC", "Ban liên Chính phủ về biến đổi khí hậu"]
        ]
        t1 = Table(acr_data, colWidths=[100, 300])
        t1.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), font_name),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
        ]))
        elements.append(t1)
        elements.append(Spacer(1, 15))

        elements.append(Paragraph("MỤC LỤC", bold_text))
        elements.append(Paragraph("I. Thông tin của cơ sở phải thực hiện kiểm kê khí nhà kính", normal))
        elements.append(Paragraph("II. Thông tin về hoạt động sản xuất kinh doanh và số liệu hoạt động", normal))
        elements.append(Paragraph("III. Kết quả thực hiện kiểm kê phát thải khí nhà kính", normal))
        elements.append(Paragraph("IV. Kết luận và kiến nghị", normal))
        elements.append(Spacer(1, 15))

        elements.append(Paragraph("I. Thông tin của cơ sở phải thực hiện kiểm kê khí nhà kính", bold_text))
        elements.append(Paragraph(f"1. Tên cơ sở, địa chỉ<br/>- Tên doanh nghiệp: {s.company_name}<br/>- Cơ sở: {s.facility_location}<br/>- Năm kiểm kê: {s.reporting_period}", normal))
        elements.append(Paragraph(f"2. Lĩnh vực hoạt động<br/>Lĩnh vực: {s.industry_sector}", normal))
        elements.append(Spacer(1, 10))

        elements.append(Paragraph("II. Thông tin về hoạt động sản xuất kinh doanh và số liệu hoạt động của cơ sở", bold_text))
        elements.append(Paragraph(f"1. Ranh giới và phạm vi hoạt động<br/>Ranh giới kiểm kê bao gồm toàn bộ hoạt động bên trong ranh giới cơ sở {s.facility_location}. Các nguồn phát thải được kiểm kê trong kỳ này bao gồm Phạm vi 1 (Phát thải trực tiếp từ đốt nhiên liệu) và Phạm vi 2 (Phát thải gián tiếp từ điện tiêu thụ).", normal))
        elements.append(Spacer(1, 10))

        elements.append(Paragraph("III. Kết quả thực hiện kiểm kê phát thải khí nhà kính", bold_text))
        elements.append(Paragraph("1. Phương pháp luận<br/>Kiểm kê được thực hiện dựa trên hướng dẫn của IPCC và các quy định của Bộ TN&MT (NĐ 06/2022/NĐ-CP). Phương pháp chung: PT = AD x EF", normal))
        elements.append(Spacer(1, 10))

        # Reconstruct calculations table
        elements.append(Paragraph("2. Số liệu hoạt động và hệ số phát thải", bold_text))
        table_data = [["Hoạt động", "Scope", "Khối lượng", "EF", "Phát thải (tCO2e)"]]
        for calc in report.calculations:
            table_data.append([
                calc.description, calc.scope,
                f"{calc.activity_value:,.1f} {calc.activity_unit}",
                str(calc.emission_factor_value),
                f"{calc.co2e_tonnes:,.3f}"
            ])
        t2 = Table(table_data)
        t2.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), font_name),
            ('FONTNAME', (0,0), (-1,0), font_name_bold),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
        ]))
        elements.append(t2)
        elements.append(Spacer(1, 15))

        elements.append(Paragraph("IV. Kết luận và kiến nghị", bold_text))
        elements.append(Paragraph(f"Tổng phát thải ròng của cơ sở là <b>{s.total_co2e_tonnes:,.3f} tCO2e</b>.", normal))

        doc.build(elements)
        return buffer.getvalue()



    @classmethod
    def to_excel(cls, report: AuditReport, filepath: str):
        from ecostream.reporting.excel_exporter import ExcelExporter
        ExcelExporter.export(report, filepath)
