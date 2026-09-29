"""CarbonAdvisor analyzing emission hotspots and generating 'What Should I Improve?' recommendations."""

from typing import List
from ecostream.models.activity import ActivityRecord, EmissionScope, MeasurementType
from ecostream.models.results import (
    CarbonCalculation,
    ReliabilityAssessment,
    ReductionRecommendation,
    SMEInventorySummary,
    ScopeBreakdown,
)


class CarbonAdvisor:
    """Provides decision support, hotspot detection, and data collection roadmaps for SMEs."""

    @classmethod
    def identify_hotspots(cls, calculations: List[CarbonCalculation], limit: int = 5) -> List[CarbonCalculation]:
        """Rank emissions descending by carbon impact."""
        return sorted(calculations, key=lambda c: c.co2e_tonnes, reverse=True)[:limit]

    @classmethod
    def generate_recommendations(
        cls,
        records: List[ActivityRecord],
        calculations: List[CarbonCalculation],
        total_tonnes: float,
    ) -> List[ReductionRecommendation]:
        recs: List[ReductionRecommendation] = []
        calc_map = {c.activity_id: c for c in calculations}

        # 1. Detect Spend-Based Proxies in Scope 3 (Top Data Quality Upgrade)
        spend_records = [r for r in records if r.measurement_type == MeasurementType.SPEND_BASED_PROXY]
        if spend_records:
            affected_ids = [r.id for r in spend_records]
            spend_tonnes = sum(calc_map[r.id].co2e_tonnes for r in spend_records if r.id in calc_map)
            spend_pct = round((spend_tonnes / max(0.001, total_tonnes)) * 100.0, 1)

            recs.append(
                ReductionRecommendation(
                    id="REC-DATA-01",
                    title="Nâng cấp dữ liệu vận tải & mua hàng từ chi phí (VNĐ) sang số liệu vật lý",
                    priority="HIGH",
                    category="DATA_QUALITY_UPGRADE",
                    current_gap=(
                        f"Đang có {len(spend_records)} hạng mục ({spend_tonnes:.2f} tCO2e, chiếm {spend_pct}%) "
                        "sử dụng hệ số ước tính theo số tiền (Spend-based proxy) với sai số lên tới ±40%."
                    ),
                    action_required=(
                        "Yêu cầu nhà xe/đơn vị logistics cung cấp bảng kê quãng đường (km) và khối lượng hàng (tấn); "
                        "yêu cầu nhà cung cấp vật liệu ghi rõ số kg trên hóa đơn VAT thay vì chỉ ghi tổng tiền dịch vụ."
                    ),
                    potential_confidence_gain_pct=14.5,
                    target_scope=EmissionScope.SCOPE_3,
                    affected_item_ids=affected_ids,
                )
            )

        # 2. Scope 2 Electricity Optimization
        scope_2_calcs = [c for c in calculations if c.scope == EmissionScope.SCOPE_2]
        if scope_2_calcs:
            elec_tonnes = sum(c.co2e_tonnes for c in scope_2_calcs)
            elec_pct = round((elec_tonnes / max(0.001, total_tonnes)) * 100.0, 1)
            if elec_pct >= 30.0:
                recs.append(
                    ReductionRecommendation(
                        id="REC-DECARB-01",
                        title="Tối ưu phát thải điện lưới (Scope 2 Hotspot)",
                        priority="HIGH",
                        category="DECARBONIZATION_ROADMAP",
                        current_gap=(
                            f"Điện lưới quốc gia chiếm tới {elec_pct}% tổng phát thải doanh nghiệp ({elec_tonnes:.2f} tCO2e). "
                            "Hệ số phát thải lưới điện Việt Nam (0.7221 kg CO2/kWh) là nguồn phát thải chủ chốt."
                        ),
                        action_required=(
                            "1. Kiểm toán năng lượng hệ thống máy nén khí, động cơ công nghiệp và chiếu sáng LED.\n"
                            "2. Xem xét mô hình đầu tư điện mặt trời mái nhà (Rooftop Solar) tự dùng để giảm trực tiếp lượng kWh mua từ EVN."
                        ),
                        potential_confidence_gain_pct=5.0,
                        target_scope=EmissionScope.SCOPE_2,
                        affected_item_ids=[c.activity_id for c in scope_2_calcs],
                    )
                )

        # 3. Scope 1 Generator / Mobile Fleet Efficiency
        scope_1_calcs = [c for c in calculations if c.scope == EmissionScope.SCOPE_1]
        if scope_1_calcs:
            s1_tonnes = sum(c.co2e_tonnes for c in scope_1_calcs)
            recs.append(
                ReductionRecommendation(
                    id="REC-SCOPE1-01",
                    title="Chuẩn hóa nhật ký tiêu hao nhiên liệu máy phát và phương tiện",
                    priority="MEDIUM",
                    category="DATA_QUALITY_UPGRADE",
                    current_gap=(
                        f"Phát thải trực tiếp Scope 1 đạt {s1_tonnes:.2f} tCO2e. Hiện đã có hóa đơn nhiên liệu Petrolimex "
                        "nhưng chưa có nhật ký phân tách giờ chạy máy phát và định mức tiêu hao từng xe."
                    ),
                    action_required=(
                        "Số hóa sổ giao nhận nhiên liệu nội bộ, ghi nhận số giờ chạy máy phát điện dự phòng "
                        "và số km công tơ mét từng xe hàng tháng để giám sát định mức tiêu hao."
                    ),
                    potential_confidence_gain_pct=6.0,
                    target_scope=EmissionScope.SCOPE_1,
                    affected_item_ids=[c.activity_id for c in scope_1_calcs],
                )
            )

        # 4. Check for OCR-extracted or scanned records
        ocr_records = [
            r for r in records
            if "OCR" in (r.evidence.extraction_method or "") or r.evidence.document_type.endswith("_OCR")
        ]
        if ocr_records:
            recs.append(
                ReductionRecommendation(
                    id="REC-OCR-UPGRADE",
                    title="Chuyển đổi chứng từ ảnh scan sang hóa đơn điện tử số có chữ ký điện tử",
                    priority="LOW",
                    category="DATA_QUALITY_UPGRADE",
                    current_gap=(
                        f"Có {len(ocr_records)} hoạt động trích xuất từ chứng từ qua cơ chế OCR (ảnh/scan). "
                        "Dù bóc tách thành công, dữ liệu scan vẫn chịu biên độ kiểm tra chất lượng chặt chẽ hơn."
                    ),
                    action_required=(
                        "Lưu trữ và upload trực tiếp hóa đơn điện tử gốc dạng PDF/XML từ nhà cung cấp "
                        "để tối đa hóa chỉ số Extraction Confidence lên mức Audit-Ready tuyệt đối."
                    ),
                    potential_confidence_gain_pct=4.0,
                    target_scope=EmissionScope.SCOPE_3,
                    affected_item_ids=[r.id for r in ocr_records],
                )
            )

        return recs

    @classmethod
    def compile_summary(
        cls,
        company_name: str,
        facility_location: str,
        reporting_period: str,
        industry_sector: str,
        records: List[ActivityRecord],
        calculations: List[CarbonCalculation],
        scopes: List[ScopeBreakdown],
        total_tonnes: float,
        total_min: float,
        total_max: float,
        reliability: ReliabilityAssessment,
    ) -> SMEInventorySummary:
        scope_map = {s.scope: s.total_tonnes for s in scopes}
        hotspots = cls.identify_hotspots(calculations)
        recommendations = cls.generate_recommendations(records, calculations, total_tonnes)

        return SMEInventorySummary(
            company_name=company_name,
            facility_location=facility_location,
            reporting_period=reporting_period,
            industry_sector=industry_sector,
            total_co2e_tonnes=total_tonnes,
            total_uncertainty_min_tonnes=total_min,
            total_uncertainty_max_tonnes=total_max,
            scope_1_tonnes=scope_map.get(EmissionScope.SCOPE_1, 0.0),
            scope_2_tonnes=scope_map.get(EmissionScope.SCOPE_2, 0.0),
            scope_3_tonnes=scope_map.get(EmissionScope.SCOPE_3, 0.0),
            scopes=scopes,
            reliability=reliability,
            hotspots=hotspots,
            recommendations=recommendations,
        )

    # Backward compatibility alias
    generate_inventory_summary = compile_summary
