"""ReliabilityEngine assessing the 5-dimensional EcoStream Carbon Confidence Score."""

from typing import List
from ecostream.models.activity import ActivityRecord, MeasurementType
from ecostream.models.results import ReliabilityAssessment, DimensionScore


class ReliabilityEngine:
    """Evaluates data quality, traceability, and confidence indices for SME carbon disclosures."""

    @classmethod
    def evaluate(cls, records: List[ActivityRecord]) -> ReliabilityAssessment:
        if not records:
            return cls._empty_assessment()

        n = len(records)
        avg_comp = sum(r.quality.completeness_score for r in records) / n
        avg_temp = sum(r.quality.temporal_score for r in records) / n
        avg_geo = sum(r.quality.geographical_score for r in records) / n
        avg_src = sum(r.quality.source_reliability_score for r in records) / n
        avg_extr = sum(r.quality.extraction_confidence_score for r in records) / n

        # Check spend-based vs primary data breakdown
        spend_count = sum(1 for r in records if r.measurement_type == MeasurementType.SPEND_BASED_PROXY)
        primary_count = sum(
            1 for r in records if r.measurement_type in (MeasurementType.PRIMARY_METERED, MeasurementType.PRIMARY_INVOICED)
        )
        spend_ratio = round((spend_count / n) * 100.0, 1)
        primary_ratio = round((primary_count / n) * 100.0, 1)

        # Composite overall index (0 - 100)
        overall_score = round(
            (0.25 * avg_comp + 0.15 * avg_temp + 0.20 * avg_geo + 0.25 * avg_src + 0.15 * avg_extr) * 100.0,
            1,
        )

        if overall_score >= 85.0:
            grade = "A"
            label = "Audit-Ready (Sẵn sàng kiểm toán CBAM / ESG)"
            verdict = "Dữ liệu có độ tin cậy rất cao, truy xuất nguồn gốc rõ ràng và sử dụng hệ số phát thải đặc thù Việt Nam."
        elif overall_score >= 70.0:
            grade = "B"
            label = "Fair / Actionable (Khá tốt, có thể hành động)"
            verdict = "Dữ liệu đủ tin cậy cho báo cáo nội bộ và bước đầu kiểm kê, một số hạng mục Scope 3 cần nâng cấp chứng từ gốc."
        elif overall_score >= 50.0:
            grade = "C"
            label = "Needs Improvement (Cần bổ sung chứng từ gốc)"
            verdict = "Tỷ lệ ước tính hoặc dữ liệu thứ cấp còn cao, biên độ không chắc chắn lớn, rủi ro bị xuất toán khi kiểm toán quốc tế."
        else:
            grade = "D"
            label = "High Risk (Rủi ro dữ liệu cao)"
            verdict = "Thiếu hụt dữ liệu hoạt động sơ cấp nghiêm trọng. Cần thiết lập quy trình thu thập dữ liệu cơ bản."

        dimensions = {
            "completeness": DimensionScore(
                name="Tính đầy đủ (Completeness)",
                score=round(avg_comp * 100.0, 1),
                grade=cls._grade_for(avg_comp * 100.0),
                explanation="Mức độ đầy đủ của các trường thông tin bắt buộc (sản lượng, đơn vị tính, chu kỳ thời gian).",
            ),
            "temporal": DimensionScore(
                name="Đồng bộ thời gian (Temporal Alignment)",
                score=round(avg_temp * 100.0, 1),
                grade=cls._grade_for(avg_temp * 100.0),
                explanation="Độ khớp thời gian của chứng từ đối với kỳ báo cáo (tháng/năm).",
            ),
            "geographical": DimensionScore(
                name="Tính đặc thù địa phương (Geographical Fit)",
                score=round(avg_geo * 100.0, 1),
                grade=cls._grade_for(avg_geo * 100.0),
                explanation="Mức độ sử dụng hệ số phát thải cụ thể của Việt Nam (Lưới điện MONRE, xăng dầu TCVN) thay vì chỉ số toàn cầu.",
            ),
            "source_reliability": DimensionScore(
                name="Chất lượng nguồn dữ liệu (Source Reliability)",
                score=round(avg_src * 100.0, 1),
                grade=cls._grade_for(avg_src * 100.0),
                explanation="Tỷ trọng dữ liệu sơ cấp đo đếm (công tơ, hóa đơn điện tử) so với các ước tính gián tiếp dựa trên chi phí.",
            ),
            "extraction_confidence": DimensionScore(
                name="Độ tin cậy trích xuất AI (Extraction Confidence)",
                score=round(avg_extr * 100.0, 1),
                grade=cls._grade_for(avg_extr * 100.0),
                explanation="Độ chuẩn xác và bằng chứng số dòng/ảnh chụp khi trích xuất dữ liệu tự động từ tài liệu.",
            ),
        }

        return ReliabilityAssessment(
            overall_confidence_score=overall_score,
            grade=grade,
            grade_label=label,
            summary_verdict=verdict,
            dimensions=dimensions,
            spend_based_ratio_pct=spend_ratio,
            primary_data_ratio_pct=primary_ratio,
        )

    @staticmethod
    def _grade_for(score: float) -> str:
        if score >= 85:
            return "A"
        if score >= 70:
            return "B"
        if score >= 50:
            return "C"
        return "D"

    @classmethod
    def _empty_assessment(cls) -> ReliabilityAssessment:
        return ReliabilityAssessment(
            overall_confidence_score=0.0,
            grade="D",
            grade_label="No Data",
            summary_verdict="Chưa có dữ liệu nào được phân tích.",
            dimensions={},
            spend_based_ratio_pct=0.0,
            primary_data_ratio_pct=0.0,
        )
