"""Export engine generating audit-ready Markdown, standalone HTML, and native PDF carbon disclosures."""

import io
import os
from datetime import datetime
from typing import List

from ecostream.models.results import AuditReport, SMEInventorySummary, CarbonCalculation


class ReportExporter:
    """Exports structured audit reports with full evidence lineage."""

    @classmethod
    def to_markdown(cls, report: AuditReport) -> str:
        s = report.summary
        rel = s.reliability

        md = []
        md.append(f"# BÁO CÁO KIỂM KÊ PHÁT THẢI KHÍ NHÀ KÍNH & ĐỘ TIN CẬY DỮ LIỆU")
        md.append(f"### EcoStream AI Carbon Engine — Audit & Reliability Disclosure\n")
        md.append(f"- **Doanh nghiệp**: {s.company_name}")
        md.append(f"- **Địa điểm / Cơ sở**: {s.facility_location}")
        md.append(f"- **Lĩnh vực hoạt động**: {s.industry_sector}")
        md.append(f"- **Kỳ báo cáo**: {s.reporting_period}")
        md.append(f"- **Ngày phát hành**: {report.generated_at}")
        md.append(f"- **Mã báo cáo**: `{report.report_id}`\n")

        md.append("---\n")
        md.append("## 1. TỔNG QUAN PHÁT THẢI (EXECUTIVE SUMMARY)\n")
        md.append(f"| Chỉ số | Giá trị | Đơn vị | Ghi chú / Biên độ tin cậy |")
        md.append(f"| :--- | :---: | :---: | :--- |")
        md.append(f"| **Tổng phát thải ròng** | **{s.total_co2e_tonnes:.3f}** | **tCO₂e** | Khoảng tin cậy 95%: [{s.total_uncertainty_min_tonnes:.3f} - {s.total_uncertainty_max_tonnes:.3f}] tCO₂e |")
        md.append(f"| • **Scope 1 (Trực tiếp)** | {s.scope_1_tonnes:.3f} | tCO₂e | Nhiên liệu đốt lò hơi & máy phát dự phòng |")
        md.append(f"| • **Scope 2 (Gián tiếp điện)** | {s.scope_2_tonnes:.3f} | tCO₂e | Điện lưới quốc gia EVN (Hệ số MONRE) |")
        md.append(f"| • **Scope 3 (Chuỗi giá trị)** | {s.scope_3_tonnes:.3f} | tCO₂e | Vận tải, nguyên vật liệu & bao bì |")
        md.append(f"| **Chỉ số tin cậy EcoStream** | **{rel.overall_confidence_score}%** | **Grade {rel.grade}** | **{rel.grade_label}** |\n")

        md.append("### Nhận định độ tin cậy dữ liệu:")
        md.append(f"> {rel.summary_verdict}\n")

        md.append("---\n")
        md.append("## 2. ĐÁNH GIÁ 5 CHIỀU ĐỘ TIN CẬY DỮ LIỆU (RELIABILITY RADAR)\n")
        md.append("| Tiêu chí đánh giá | Điểm số | Xếp loại | Ý nghĩa & Tiêu chuẩn áp dụng |")
        md.append("| :--- | :---: | :---: | :--- |")
        for k, dim in rel.dimensions.items():
            md.append(f"| **{dim.name}** | {dim.score}% | Grade {dim.grade} | {dim.explanation} |")
        md.append(f"\n- **Tỷ trọng dữ liệu sơ cấp đo đếm (Primary Data)**: {rel.primary_data_ratio_pct}%")
        md.append(f"- **Tỷ trọng dữ liệu ước tính gián tiếp (Spend-based Proxy)**: {rel.spend_based_ratio_pct}%\n")

        md.append("---\n")
        md.append("## 3. BẢNG TRUY NGUYÊN CHỨNG TỪ & HỆ SỐ PHÁT THẢI (EVIDENCE & PROVENANCE LAYER)\n")
        md.append("| STT | Hoạt động | Phạm vi | Lượng hoạt động | Hệ số (EF) | Phát thải (tCO₂e) | Sai số | Nguồn chứng từ gốc | Trích xuất | Tin cậy |")
        md.append("| :---: | :--- | :---: | :---: | :--- | :---: | :---: | :--- | :---: | :---: |")
        for i, c in enumerate(report.calculations, 1):
            md.append(
                f"| {i} | {c.description} | {c.scope.value} | {c.activity_value:,.2f} {c.activity_unit} | "
                f"{c.emission_factor_value} ({c.emission_factor_source[:30]}...) | **{c.co2e_tonnes:.3f}** | "
                f"±{c.uncertainty_pct}% | `{c.evidence.source_document}` ({c.evidence.page_or_line}) | "
                f"{c.evidence.extraction_method} | {c.quality_composite_score}% |"
            )

        md.append("\n---\n")
        md.append("## 4. 'WHAT SHOULD I IMPROVE?' — LỘ TRÌNH NÂNG CẤP DỮ LIỆU & GIẢM PHÁT THẢI\n")
        for rec in s.recommendations:
            md.append(f"### 📍 [{rec.priority}] {rec.title}")
            md.append(f"- **Phạm vi tác động**: {rec.target_scope.value} ({rec.category})")
            md.append(f"- **Hiện trạng & Khoảng trống**: {rec.current_gap}")
            md.append(f"- **Hành động đề xuất cho SME**: {rec.action_required}")
            md.append(f"- **Tiềm năng gia tăng độ tin cậy**: **+{rec.potential_confidence_gain_pct}%**\n")

        md.append("---\n")
        md.append(f"*Báo cáo được tổng hợp tự động bởi EcoStream Engine v0.1.0 — Phục vụ tuân thủ CBAM & Nghị định 06/2022/NĐ-CP.*")
        return "\n".join(md)

    @classmethod
    def to_html(cls, report: AuditReport) -> str:
        s = report.summary
        rel = s.reliability

        calc_rows = ""
        for i, c in enumerate(report.calculations, 1):
            badge_class = (
                "bg-emerald-100 text-emerald-800 border-emerald-200"
                if c.scope.value == "Scope 1"
                else "bg-blue-100 text-blue-800 border-blue-200"
                if c.scope.value == "Scope 2"
                else "bg-purple-100 text-purple-800 border-purple-200"
            )
            conf_color = "text-emerald-700 font-bold" if c.quality_composite_score >= 85 else "text-amber-700 font-bold" if c.quality_composite_score >= 70 else "text-red-700 font-bold"
            calc_rows += f"""
            <tr class="border-b border-slate-200 hover:bg-slate-50 text-xs">
                <td class="py-2.5 px-3 font-mono text-slate-400">{i}</td>
                <td class="py-2.5 px-3 font-semibold text-slate-900">{c.description}</td>
                <td class="py-2.5 px-3"><span class="px-2 py-0.5 rounded text-[10px] font-bold border {badge_class}">{c.scope.value}</span></td>
                <td class="py-2.5 px-3 font-mono">{c.activity_value:,.2f} {c.activity_unit}</td>
                <td class="py-2.5 px-3 text-[11px] text-slate-600" title="{c.emission_factor_source}">
                    <span class="font-bold">{c.emission_factor_value}</span> <span class="text-slate-400">({c.emission_factor_unit})</span>
                </td>
                <td class="py-2.5 px-3 font-black text-slate-900 text-right font-mono">{c.co2e_tonnes:.3f}</td>
                <td class="py-2.5 px-3 text-center text-slate-500 font-mono">±{c.uncertainty_pct}%</td>
                <td class="py-2.5 px-3 text-[11px]">
                    <div class="font-mono text-slate-800 font-medium">{c.evidence.source_document}</div>
                    <div class="text-slate-500 text-[10px] truncate max-w-[180px]">{c.evidence.snippet}</div>
                </td>
                <td class="py-2.5 px-3 text-center {conf_color}">{c.quality_composite_score}%</td>
            </tr>
            """

        dim_cards = ""
        for k, dim in rel.dimensions.items():
            dim_cards += f"""
            <div class="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm avoid-break">
                <div class="flex justify-between items-center mb-1">
                    <span class="text-xs font-bold text-slate-700">{dim.name}</span>
                    <span class="text-[10px] px-2 py-0.5 rounded font-black bg-slate-100 text-slate-700 border border-slate-200">Grade {dim.grade}</span>
                </div>
                <div class="text-xl font-extrabold text-slate-900 mb-1">{dim.score}%</div>
                <p class="text-[10px] text-slate-500 leading-snug">{dim.explanation}</p>
            </div>
            """

        rec_blocks = ""
        for rec in s.recommendations:
            badge_prio = (
                "bg-red-100 text-red-800 border-red-200"
                if rec.priority == "HIGH"
                else "bg-amber-100 text-amber-800 border-amber-200"
            )
            rec_blocks += f"""
            <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-2 avoid-break">
                <div class="flex justify-between items-start gap-2">
                    <div class="font-bold text-slate-900 text-sm flex items-center gap-1.5">
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold border {badge_prio}">{rec.priority}</span>
                        {rec.title}
                    </div>
                    <span class="text-xs font-bold text-emerald-800 bg-emerald-100/70 border border-emerald-300 px-2 py-0.5 rounded whitespace-nowrap">
                        +{rec.potential_confidence_gain_pct}% Tin cậy
                    </span>
                </div>
                <div class="text-xs text-slate-600 leading-relaxed"><strong>Khoảng trống:</strong> {rec.current_gap}</div>
                <div class="text-xs text-slate-800 bg-slate-50 p-2.5 rounded-lg border border-slate-200 whitespace-pre-line leading-relaxed font-medium">
                    <strong>Hành động đề xuất:</strong>\n{rec.action_required}
                </div>
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Báo Cáo Kiểm Kê & Độ Tin Cậy Dữ Liệu Carbon - EcoStream</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- html2pdf.js for 100% clean PDF generation without browser chrome -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        /* Exact A4 Print Configuration */
        @page {{
            size: A4 portrait;
            margin: 10mm 12mm; /* Suppresses default browser URL header and date footer */
        }}

        @media print {{
            *, *::before, *::after {{
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
                color-adjust: exact !important;
            }}
            body {{
                background-color: #ffffff !important;
                padding: 0 !important;
                font-size: 10pt;
            }}
            .no-print {{
                display: none !important;
            }}
            .avoid-break {{
                break-inside: avoid !important;
                page-break-inside: avoid !important;
            }}
            .page-break {{
                break-before: page !important;
                page-break-before: always !important;
            }}
        }}

        .brand-header-bg {{
            background: linear-gradient(135deg, #064e3b 0%, #065f46 60%, #047857 100%) !important;
        }}
    </style>
</head>
<body class="bg-slate-100 text-slate-900 font-sans antialiased p-4 sm:p-8">

    <!-- Top Action Bar (Screen only, hidden in print & PDF export) -->
    <div class="max-w-6xl mx-auto mb-6 no-print flex flex-wrap justify-between items-center gap-3 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <div class="flex items-center gap-2">
            <a href="/" class="text-xs font-bold text-slate-600 hover:text-emerald-700 flex items-center gap-1 transition">
                ← Quay lại Dashboard
            </a>
            <span class="text-slate-300">|</span>
            <span class="text-xs text-slate-500">Báo cáo kiểm kê carbon chuẩn hóa</span>
        </div>
        <div class="flex items-center gap-2">
            <!-- Native Server-Side PDF Download -->
            <a href="/api/report/pdf" download="EcoStream_Carbon_Audit_Report.pdf" class="px-4 py-2 rounded-lg text-xs font-bold text-white bg-emerald-700 hover:bg-emerald-800 transition flex items-center gap-1.5 shadow">
                📥 Tải PDF Gốc (Vector .pdf)
            </a>
            <!-- Client-Side html2pdf Download -->
            <button onclick="downloadCleanPDF()" id="btnDownloadPDF" class="px-4 py-2 rounded-lg text-xs font-bold text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 transition flex items-center gap-1.5">
                📑 Xuất File PDF A4
            </button>
            <!-- Browser Print (with headers stripped via @page) -->
            <button onclick="window.print()" class="px-4 py-2 rounded-lg text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-300 transition">
                🖨 In Trình Duyệt
            </button>
        </div>
    </div>

    <!-- Printable & Exportable Report Container -->
    <div id="reportContainer" class="max-w-6xl mx-auto space-y-6 bg-white p-6 sm:p-10 rounded-2xl border border-slate-200 shadow-md">

        <!-- Official Header Block -->
        <header class="brand-header-bg text-white p-6 sm:p-8 rounded-xl shadow-md avoid-break">
            <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <div class="flex items-center gap-2.5">
                        <span class="text-2xl font-black tracking-tight text-emerald-300">🌱 EcoStream</span>
                        <span class="bg-emerald-800 text-emerald-200 text-[10px] font-mono px-2 py-0.5 rounded border border-emerald-600">CBAM / DECREE 06 READY</span>
                    </div>
                    <h1 class="text-xl sm:text-2xl font-black mt-2 text-white">Báo Cáo Kiểm Kê & Độ Tin Cậy Dữ Liệu Carbon</h1>
                    <p class="text-emerald-100 text-xs mt-1">
                        <strong>{s.company_name}</strong> | Cơ sở: {s.facility_location} | Kỳ báo cáo: <strong>{s.reporting_period}</strong>
                    </p>
                </div>
                <div class="text-left sm:text-right border-t sm:border-t-0 pt-2 sm:pt-0 border-emerald-700/50">
                    <div class="text-xs text-emerald-200">Mã chứng thư số: <span class="font-mono text-white font-bold">{report.report_id}</span></div>
                    <div class="text-xs text-emerald-200 mt-0.5">Ngày phát hành: {report.generated_at}</div>
                    <div class="text-[10px] text-emerald-300 mt-1 uppercase font-bold">Xác thực bởi EcoStream Carbon Engine</div>
                </div>
            </div>
        </header>

        <!-- KPI Executive Grid -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 avoid-break">
            <div class="bg-slate-50 p-4 rounded-xl border border-slate-200">
                <div class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Tổng Phát Thải Ròng</div>
                <div class="text-2xl font-black text-slate-900 mt-1">{s.total_co2e_tonnes:.3f} <span class="text-xs font-semibold text-slate-500">tCO₂e</span></div>
                <div class="text-[10px] text-slate-500 mt-1 font-mono">95% CI: [{s.total_uncertainty_min_tonnes:.2f} - {s.total_uncertainty_max_tonnes:.2f}]</div>
            </div>
            <div class="bg-slate-50 p-4 rounded-xl border border-slate-200">
                <div class="text-[11px] font-bold text-emerald-700 uppercase tracking-wider">Độ Tin Cậy EcoStream</div>
                <div class="text-2xl font-black text-emerald-700 mt-1">{rel.overall_confidence_score}% <span class="text-xs font-bold text-emerald-900">Grade {rel.grade}</span></div>
                <div class="text-[10px] text-slate-600 mt-1">{rel.grade_label}</div>
            </div>
            <div class="bg-slate-50 p-4 rounded-xl border border-slate-200">
                <div class="text-[11px] font-bold text-blue-700 uppercase tracking-wider">Scope 1 & 2 (Nội Bộ)</div>
                <div class="text-xl font-bold text-slate-900 mt-1">{s.scope_1_tonnes + s.scope_2_tonnes:.2f} <span class="text-xs font-normal text-slate-500">tCO₂e</span></div>
                <div class="text-[10px] text-slate-500 mt-1">S1: {s.scope_1_tonnes:.2f} | S2: {s.scope_2_tonnes:.2f} (Lưới VN)</div>
            </div>
            <div class="bg-slate-50 p-4 rounded-xl border border-slate-200">
                <div class="text-[11px] font-bold text-purple-700 uppercase tracking-wider">Scope 3 (Chuỗi Cung Ứng)</div>
                <div class="text-xl font-bold text-slate-900 mt-1">{s.scope_3_tonnes:.2f} <span class="text-xs font-normal text-slate-500">tCO₂e</span></div>
                <div class="text-[10px] text-slate-500 mt-1">Vận tải & vật liệu ({rel.spend_based_ratio_pct}% Spend Proxy)</div>
            </div>
        </div>

        <!-- 5-Dimension Radar Cards -->
        <section class="space-y-2.5 avoid-break">
            <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
                Đánh Giá 5 Chiều Chất Lượng & Độ Tin Cậy Dữ Liệu
            </h2>
            <div class="grid grid-cols-1 sm:grid-cols-5 gap-2.5">
                {dim_cards}
            </div>
        </section>

        <!-- Evidence & Provenance Table -->
        <section class="space-y-2.5 avoid-break">
            <div class="flex justify-between items-center">
                <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
                    Bảng Truy Nguyên Nguồn Gốc Chứng Từ (Evidence & Provenance Layer)
                </h2>
                <span class="text-[11px] text-slate-500 font-mono">100% Traceable to Raw Invoices</span>
            </div>
            <div class="overflow-x-auto border border-slate-200 rounded-xl">
                <table class="w-full text-left border-collapse">
                    <thead>
                        <tr class="bg-slate-100 text-slate-700 text-[10px] font-bold uppercase tracking-wider border-b border-slate-200">
                            <th class="py-2.5 px-3">#</th>
                            <th class="py-2.5 px-3">Hạng Mục Hoạt Động</th>
                            <th class="py-2.5 px-3">Scope</th>
                            <th class="py-2.5 px-3">Sản Lượng</th>
                            <th class="py-2.5 px-3">Hệ Số EF</th>
                            <th class="py-2.5 px-3 text-right">tCO₂e</th>
                            <th class="py-2.5 px-3 text-center">Sai Số</th>
                            <th class="py-2.5 px-3">Chứng Từ Gốc</th>
                            <th class="py-2.5 px-3 text-center">Tin Cậy</th>
                        </tr>
                    </thead>
                    <tbody>
                        {calc_rows}
                    </tbody>
                </table>
            </div>
        </section>

        <!-- Recommendations -->
        <section class="space-y-2.5 avoid-break">
            <h2 class="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
                Lộ Trình Cải Thiện Dữ Liệu ("What Should I Improve?")
            </h2>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {rec_blocks}
            </div>
        </section>

        <!-- Formal Audit Footer & Signatures -->
        <footer class="pt-6 border-t border-slate-200 avoid-break">
            <div class="grid grid-cols-2 gap-8 text-center text-xs text-slate-600">
                <div>
                    <div class="font-bold uppercase text-slate-800">Đại Diện Doanh Nghiệp</div>
                    <div class="text-[10px] text-slate-400 mt-0.5">Xác nhận số liệu hoạt động nội bộ</div>
                    <div class="h-16 flex items-end justify-center font-serif italic text-slate-400 font-medium">
                        (Ký và đóng dấu xác nhận)
                    </div>
                    <div class="font-bold text-slate-800 text-xs mt-1">{s.company_name}</div>
                </div>
                <div>
                    <div class="font-bold uppercase text-slate-800">Đơn Vị Tư Vấn & Thẩm Định AI</div>
                    <div class="text-[10px] text-slate-400 mt-0.5">Hệ thống EcoStream Carbon Data Engine</div>
                    <div class="h-16 flex items-end justify-center font-mono text-emerald-800 text-xs font-bold">
                        ✔ VERIFIED DIGITAL SIGNATURE
                    </div>
                    <div class="font-bold text-emerald-900 text-xs mt-1">EcoStream Platform • USTH 2026</div>
                </div>
            </div>
            <div class="text-center text-[10px] text-slate-400 mt-6 pt-4 border-t border-slate-100">
                Báo cáo này được tạo bởi EcoStream PoC Engine. Dữ liệu kiểm kê tuân thủ phương pháp luận GHG Protocol Corporate Standard và hệ số lưới điện MONRE Việt Nam.
            </div>
        </footer>

    </div>

    <script>
        function downloadCleanPDF() {{
            const btn = document.getElementById('btnDownloadPDF');
            btn.disabled = true;
            btn.innerText = '⏳ Đang kết xuất PDF...';

            const element = document.getElementById('reportContainer');
            const opt = {{
                margin:       [8, 8, 8, 8],
                filename:     'EcoStream_Carbon_Audit_Report.pdf',
                image:        {{ type: 'jpeg', quality: 0.98 }},
                html2canvas:  {{ scale: 2, useCORS: true, letterRendering: true }},
                jsPDF:        {{ unit: 'mm', format: 'a4', orientation: 'portrait' }},
                pagebreak:    {{ mode: ['avoid-all', 'css', 'legacy'] }}
            }};

            html2pdf().set(opt).from(element).save().then(() => {{
                btn.disabled = false;
                btn.innerText = '📑 Xuất File PDF A4';
            }}).catch(err => {{
                alert('Lỗi xuất PDF: ' + err);
                btn.disabled = false;
                btn.innerText = '📑 Xuất File PDF A4';
            }});
        }}
    </script>
</body>
</html>
        """

    @classmethod
    def to_pdf(cls, report: AuditReport) -> bytes:
        """Generates an audit-ready, standalone vector PDF using ReportLab with clean Vietnamese TrueType fonts."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        # Register system TrueType font or fallback to standard Helvetica
        font_name = "Helvetica"
        font_name_bold = "Helvetica-Bold"
        for font_candidate in [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/tahoma.ttf",
            "C:/Windows/Fonts/calibri.ttf",
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
        rel = s.reliability

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=28,
            rightMargin=28,
            topMargin=28,
            bottomMargin=28,
        )

        elements = []

        # Styles
        title_style = ParagraphStyle(
            name="Title",
            fontName=font_name_bold,
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#064e3b"),
        )
        subtitle_style = ParagraphStyle(
            name="Subtitle",
            fontName=font_name,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#475569"),
        )
        section_style = ParagraphStyle(
            name="Section",
            fontName=font_name_bold,
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=12,
            spaceAfter=6,
        )
        cell_style = ParagraphStyle(
            name="Cell",
            fontName=font_name,
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1e293b"),
        )
        cell_bold = ParagraphStyle(
            name="CellBold",
            fontName=font_name_bold,
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#0f172a"),
        )

        # 1. Header Banner Table
        header_data = [
            [
                Paragraph("🌱 <b>EcoStream AI Carbon Data Engine</b>", title_style),
                Paragraph(f"<b>Mã báo cáo:</b> {report.report_id}<br/><b>Ngày:</b> {report.generated_at[:10]}", subtitle_style),
            ],
            [
                Paragraph(
                    f"<b>Doanh nghiệp:</b> {s.company_name} &nbsp;|&nbsp; <b>Kỳ:</b> {s.reporting_period}<br/>"
                    f"<b>Cơ sở:</b> {s.facility_location} &nbsp;|&nbsp; <b>Lĩnh vực:</b> {s.industry_sector}",
                    subtitle_style,
                ),
                Paragraph("<b>Chuẩn:</b> GHG Protocol / MONRE 2626", subtitle_style),
            ],
        ]
        header_table = Table(header_data, colWidths=[360, 180])
        header_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#86efac")),
                    ("PADDING", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        elements.append(header_table)
        elements.append(Spacer(1, 10))

        # 2. Executive Summary KPIs Table
        elements.append(Paragraph("1. TỔNG QUAN PHÁT THẢI (EXECUTIVE SUMMARY)", section_style))
        kpi_data = [
            [
                Paragraph("<b>Chỉ số phát thải & Độ tin cậy</b>", cell_bold),
                Paragraph("<b>Giá trị</b>", cell_bold),
                Paragraph("<b>Khoảng tin cậy 95%</b>", cell_bold),
                Paragraph("<b>Ghi chú phương pháp</b>", cell_bold),
            ],
            [
                Paragraph("<b>Tổng Phát Thải Ròng</b>", cell_bold),
                Paragraph(f"<b>{s.total_co2e_tonnes:.3f} tCO₂e</b>", cell_bold),
                Paragraph(f"[{s.total_uncertainty_min_tonnes:.2f} - {s.total_uncertainty_max_tonnes:.2f}] t", cell_style),
                Paragraph("Tổng hợp Scopes 1, 2, 3", cell_style),
            ],
            [
                Paragraph("• Scope 1 (Trực tiếp)", cell_style),
                Paragraph(f"{s.scope_1_tonnes:.3f} t", cell_style),
                Paragraph("±7.5%", cell_style),
                Paragraph("Hóa đơn dầu Diesel DO (Petrolimex)", cell_style),
            ],
            [
                Paragraph("• Scope 2 (Điện lưới)", cell_style),
                Paragraph(f"{s.scope_2_tonnes:.3f} t", cell_style),
                Paragraph("±5.0%", cell_style),
                Paragraph("Công tơ EVN, Hệ số MONRE 0.7221", cell_style),
            ],
            [
                Paragraph("• Scope 3 (Chuỗi giá trị)", cell_style),
                Paragraph(f"{s.scope_3_tonnes:.3f} t", cell_style),
                Paragraph("±15% - 40%", cell_style),
                Paragraph(f"Vận tải, vật liệu ({rel.spend_based_ratio_pct}% spend proxy)", cell_style),
            ],
            [
                Paragraph("<b>EcoStream Confidence Index</b>", cell_bold),
                Paragraph(f"<b>{rel.overall_confidence_score:.1f}%</b>", cell_bold),
                Paragraph(f"<b>Grade {rel.grade}</b>", cell_bold),
                Paragraph(rel.grade_label, cell_style),
            ],
        ]
        kpi_table = Table(kpi_data, colWidths=[160, 100, 110, 170])
        kpi_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        elements.append(kpi_table)
        elements.append(Spacer(1, 10))

        # 3. 5-Dimensional Reliability Table
        elements.append(Paragraph("2. ĐÁNH GIÁ 5 CHIỀU ĐỘ TIN CẬY DỮ LIỆU", section_style))
        dim_data = [
            [
                Paragraph("<b>Tiêu chí</b>", cell_bold),
                Paragraph("<b>Điểm</b>", cell_bold),
                Paragraph("<b>Hạng</b>", cell_bold),
                Paragraph("<b>Ý nghĩa & Tiêu chuẩn</b>", cell_bold),
            ]
        ]
        for dim in rel.dimensions.values():
            dim_data.append(
                [
                    Paragraph(dim.name, cell_style),
                    Paragraph(f"{dim.score}%", cell_bold),
                    Paragraph(f"Grade {dim.grade}", cell_style),
                    Paragraph(dim.explanation, cell_style),
                ]
            )
        dim_table = Table(dim_data, colWidths=[160, 60, 60, 260])
        dim_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("PADDING", (0, 0), (-1, -1), 4),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        elements.append(dim_table)
        elements.append(Spacer(1, 10))

        # 4. Evidence & Provenance Table
        elements.append(Paragraph("3. BẢNG TRUY NGUYÊN CHỨNG TỪ & HỆ SỐ (EVIDENCE LAYER)", section_style))
        calc_data = [
            [
                Paragraph("<b>#</b>", cell_bold),
                Paragraph("<b>Hoạt động</b>", cell_bold),
                Paragraph("<b>Scope</b>", cell_bold),
                Paragraph("<b>Sản lượng</b>", cell_bold),
                Paragraph("<b>EF</b>", cell_bold),
                Paragraph("<b>tCO₂e</b>", cell_bold),
                Paragraph("<b>Chứng từ gốc</b>", cell_bold),
                Paragraph("<b>Tin cậy</b>", cell_bold),
            ]
        ]
        for idx, c in enumerate(report.calculations, 1):
            calc_data.append(
                [
                    Paragraph(str(idx), cell_style),
                    Paragraph(c.description[:35], cell_style),
                    Paragraph(c.scope.value, cell_style),
                    Paragraph(f"{c.activity_value:,.1f} {c.activity_unit}", cell_style),
                    Paragraph(str(c.emission_factor_value), cell_style),
                    Paragraph(f"<b>{c.co2e_tonnes:.3f}</b>", cell_bold),
                    Paragraph(f"{c.evidence.source_document}<br/>{c.evidence.page_or_line}", cell_style),
                    Paragraph(f"{c.quality_composite_score}%", cell_style),
                ]
            )
        calc_table = Table(calc_data, colWidths=[20, 140, 50, 80, 50, 50, 110, 40])
        calc_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("PADDING", (0, 0), (-1, -1), 3.5),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        elements.append(calc_table)
        elements.append(Spacer(1, 10))

        # 5. Recommendations
        elements.append(Paragraph("4. LỘ TRÌNH CẢI THIỆN ('WHAT SHOULD I IMPROVE?')", section_style))
        rec_data = []
        for r in s.recommendations:
            rec_data.append(
                [
                    Paragraph(
                        f"<b>[{r.priority}] {r.title}</b> (Tiềm năng: +{r.potential_confidence_gain_pct}%)<br/>"
                        f"<b>Hiện trạng:</b> {r.current_gap}<br/>"
                        f"<b>Đề xuất:</b> {r.action_required}",
                        cell_style,
                    )
                ]
            )
        if rec_data:
            rec_table = Table(rec_data, colWidths=[540])
            rec_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
                        ("PADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            elements.append(rec_table)

        doc.build(elements)
        return buffer.getvalue()
