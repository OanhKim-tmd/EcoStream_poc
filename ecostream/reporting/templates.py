"""Vietnamese Regulatory Templates for GHG Inventories and Mitigation Filings (Mau 02 ND 06/2022)."""

from typing import List, Optional, Dict, Any
from ecostream.models.mitigation import MitigationSummary, MitigationMeasure, FacilityQuotaProfile
from ecostream.models.state import QueryLogEntry, AssumptionLogEntry
from ecostream.models.results import SMEInventorySummary, CarbonCalculation


class RegulatoryTemplates:
    """Provides standard regulatory reporting structures conforming to MONRE and Decree 06/2022."""

    @classmethod
    def render_mau_02_section_markdown(cls, mitigation: MitigationSummary) -> str:
        """Render Part 2: Mẫu số 02 Phụ lục III Nghị định 06/2022/NĐ-CP (Kế hoạch & Kết quả giảm nhẹ KNK)."""
        lines = []
        lines.append("## PHẦN II: BÁO CÁO KẾ HOẠCH & KẾT QUẢ GIẢM NHẸ PHÁT THẢI KNK")
        lines.append("*(Ban hành kèm theo Mẫu số 02 Phụ lục III Nghị định số 06/2022/NĐ-CP và sửa đổi bổ sung NĐ 119/2025/NĐ-CP)*\n")

        lines.append(f"### 1. Thông tin cơ sở & Kỳ báo cáo")
        lines.append(f"- **Tên cơ sở thực hiện giảm nhẹ**: {mitigation.facility_name}")
        lines.append(f"- **Kỳ báo cáo giảm nhẹ**: Năm {mitigation.reporting_period}")
        lines.append(f"- **Cơ sở pháp lý**: Nghị định 06/2022/NĐ-CP, Nghị định 119/2025/NĐ-CP, Thông tư 17/2022/TT-BTNMT\n")

        lines.append("### 2. Bảng tổng hợp các biện pháp giảm nhẹ phát thải KNK tại cơ sở")
        lines.append("| STT | Tên biện pháp giảm nhẹ | Lĩnh vực / Công nghệ | Phát thải cơ sở $PT_{CS}$ (tCO₂e) | Phát thải thực tế $PT$ (tCO₂e) | Mức giảm phát thải $GPT$ (tCO₂e) | Tỷ lệ giảm (%) | Phương pháp đo đếm, giám sát |")
        lines.append("| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :--- |")

        for idx, m in enumerate(mitigation.measures, start=1):
            lines.append(
                f"| {idx} | **{m.measure_name}** | {m.category.value} | {m.baseline_emissions_ptcs:,.1f} | {m.actual_emissions_pt:,.1f} | **{m.emission_reduction_gpt:,.1f}** | {m.reduction_pct:.1f}% | {m.monitoring_method} |"
            )

        lines.append(
            f"| **Tổng** | **Tổng cộng toàn cơ sở** | **Toàn bộ biện pháp** | **{mitigation.total_baseline_ptcs:,.1f}** | **{mitigation.total_actual_pt:,.1f}** | **{mitigation.total_reduction_gpt:,.1f}** | **{mitigation.overall_reduction_pct:.1f}%** | *Hệ thống SCADA, công tơ & cân điện tử* |\n"
        )

        qp = mitigation.quota_profile
        lines.append("### 3. Đánh giá tuân thủ Hạn ngạch phát thải (Emission Quota Compliance)")
        lines.append(f"- **Quyết định giao hạn ngạch**: {qp.decision_ref}")
        lines.append(f"- **Hạn ngạch phân bổ năm {qp.reporting_year} ($Quota_{{alloc}}$)**: **{qp.allocated_quota_tonnes:,.1f} tCO₂e**")
        lines.append(f"- **Tổng phát thải kiểm kê thực tế ($E_{{actual}}$)**: **{qp.actual_inventory_tonnes:,.1f} tCO₂e**")
        lines.append(f"- **Mức phát thải sau giảm nhẹ ($E_{{net}} = E_{{actual}} - GPT$)**: **{qp.net_compliance_emissions_tonnes:,.1f} tCO₂e**")

        balance_sign = "+" if qp.quota_balance_tonnes >= 0 else ""
        lines.append(f"- **Chênh lệch hạn ngạch ($\\Delta_{{Quota}}$)**: **{balance_sign}{qp.quota_balance_tonnes:,.1f} tCO₂e**")
        lines.append(f"- **Trạng thái tuân thủ**: `{qp.compliance_status}`")
        lines.append(f"- **Khuyến nghị thị trường carbon**: *{qp.market_recommendation}*\n")

        return "\n".join(lines)

    @classmethod
    def render_audit_trail_markdown(
        cls,
        queries: List[QueryLogEntry],
        assumptions: List[AssumptionLogEntry],
        calculations: List[CarbonCalculation],
    ) -> str:
        """Render Part 3: Audit Trail & Lineage (Query Log, Assumption Log, Provenance)."""
        lines = []
        lines.append("## PHẦN III: DẤU VẾT KIỂM TOÁN & NHẬT KÝ GIẢI TRÌNH (AUDIT TRAIL)")
        lines.append("*(Minh bạch hóa 100% các giả định nội suy, truy xuất nguồn dữ liệu gốc theo ISO 14064-1 & GHG Protocol)*\n")

        # Query log table
        lines.append("### 1. Nhật ký phát hiện bất thường & Truy vấn dữ liệu (Query Log)")
        if queries:
            lines.append("| Mã truy vấn | Phạm vi | Trường dữ liệu | Loại bất thường | Hiện trạng phát hiện | Hành động xử lý tự động | Khuyến nghị kiểm toán |")
            lines.append("| :--- | :---: | :--- | :--- | :--- | :--- | :--- |")
            for q in queries:
                lines.append(
                    f"| `{q.query_id}` | {q.scope} | {q.field_name} | `{q.anomaly_type.value}` | {q.detected_issue} | {q.action_taken} | {q.suggested_human_action} |"
                )
        else:
            lines.append("*Không phát hiện bất thường hoặc khoảng trống dữ liệu cần truy vấn.*")
        lines.append("")

        # Assumption log table
        lines.append("### 2. Nhật ký giả định & Phạt điểm tin cậy (Assumption Log)")
        if assumptions:
            lines.append("| Mã giả định | Tham chiếu truy vấn | Tham số áp dụng | Giá trị giả định | Căn cứ khoa học / Pháp lý | Phạt tin cậy | Tăng sai số |")
            lines.append("| :--- | :--- | :--- | :--- | :--- | :---: | :---: |")
            for a in assumptions:
                rel_q = a.related_query_id or "-"
                lines.append(
                    f"| `{a.assumption_id}` | `{rel_q}` | {a.parameter_name} | {a.assumed_value} {a.assumed_unit} | {a.justification} | -{a.confidence_penalty*100:.1f}% | +{a.uncertainty_markup_pct:.1f}% |"
                )
        else:
            lines.append("*Không cần áp dụng giả định nội suy; 100% dữ liệu có chứng từ gốc sơ cấp.*")
        lines.append("")

        return "\n".join(lines)
