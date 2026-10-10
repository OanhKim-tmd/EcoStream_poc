import re

p = '/home/oanh/cccccccccccccc/ecostream/reporting/export.py'
with open(p, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace to_pdf with a version that mirrors DOCX content
new_to_pdf = '''
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
'''

content = re.sub(r'@classmethod\n\s+def to_pdf.*?(?=\n\s+@classmethod|\Z)', new_to_pdf + '\n', content, flags=re.DOTALL)
content = re.sub(r'@classmethod\n\s+def to_markdown.*?(?=\n\s+@classmethod)', '', content, flags=re.DOTALL)
content = re.sub(r'@classmethod\n\s+def to_html.*?(?=\n\s+@classmethod)', '', content, flags=re.DOTALL)

with open(p, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched PDF")
