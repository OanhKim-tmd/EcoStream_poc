"""Deterministic math engine for Facility Greenhouse Gas Mitigation & Quota Compliance.

Follows Decree 06/2022/ND-CP (amended by Decree 119/2025/ND-CP), Circular 17/2022/TT-BTNMT,
and Circular 38/2023/TT-BCT.
"""

from typing import List, Optional
from ecostream.models.mitigation import (
    MitigationMeasure,
    FacilityQuotaProfile,
    MitigationSummary,
)


class MitigationMathEngine:
    """Computes baseline (PT_CS), actual (PT), emission reduction (GPT = PT_CS - PT), and quota compliance."""

    @classmethod
    def calculate_measure(cls, measure: MitigationMeasure) -> MitigationMeasure:
        """Compute emission reduction and reduction percentage deterministically."""
        ptcs = round(measure.baseline_emissions_ptcs, 3)
        pt = round(measure.actual_emissions_pt, 3)
        gpt = round(max(0.0, ptcs - pt), 3)

        reduction_pct = round((gpt / ptcs * 100.0), 2) if ptcs > 0 else 0.0

        return MitigationMeasure(
            measure_id=measure.measure_id,
            measure_name=measure.measure_name,
            category=measure.category,
            start_date=measure.start_date,
            description=measure.description,
            baseline_emissions_ptcs=ptcs,
            actual_emissions_pt=pt,
            emission_reduction_gpt=gpt,
            reduction_pct=reduction_pct,
            monitoring_method=measure.monitoring_method,
            uncertainty_pct=measure.uncertainty_pct,
            evidence_source=measure.evidence_source,
        )

    @classmethod
    def calculate_quota_profile(
        cls,
        facility_id: str,
        facility_name: str,
        allocated_quota_tonnes: float,
        actual_inventory_tonnes: float,
        mitigation_reductions_tonnes: float,
        reporting_year: int = 2026,
    ) -> FacilityQuotaProfile:
        """Compute quota surplus or deficit and carbon market recommendations."""
        quota_alloc = round(allocated_quota_tonnes, 3)
        actual_inv = round(actual_inventory_tonnes, 3)
        gpt_tot = round(mitigation_reductions_tonnes, 3)

        # Net emissions under compliance framework
        net_emissions = round(max(0.0, actual_inv - gpt_tot), 3)
        # Quota balance: Allocated Quota - Actual Facility Emissions
        # Under Vietnam ETS: if actual_inv <= quota_alloc => Surplus; else Deficit
        quota_balance = round(quota_alloc - actual_inv, 3)

        if quota_balance >= 0:
            status = "THẶNG DƯ HẠN NGẠCH (QUOTA SURPLUS)"
            rec = (
                f"Cơ sở dôi dư {quota_balance:,.1f} tCO2e hạn ngạch. Đủ điều kiện chuyển nhượng trên "
                "Sàn giao dịch tín chỉ carbon hoặc lưu giữ (banking) cho kỳ tuân thủ năm tiếp theo theo NĐ 119/2025/NĐ-CP."
            )
        else:
            status = "THIẾU HỤT HẠN NGẠCH (QUOTA DEFICIT)"
            deficit = abs(quota_balance)
            rec = (
                f"Cơ sở thiếu hụt {deficit:,.1f} tCO2e so với hạn ngạch được phân bổ. Cần mua bổ sung hạn ngạch "
                "hoặc bù trừ tối đa 10% bằng tín chỉ carbon hợp chuẩn (VCM/Cơ chế trao đổi) trước ngày 31/12."
            )

        return FacilityQuotaProfile(
            facility_id=facility_id,
            facility_name=facility_name,
            decision_ref="Quyết định 42/2026/QĐ-TTg & NĐ 119/2025/NĐ-CP",
            reporting_year=reporting_year,
            allocated_quota_tonnes=quota_alloc,
            actual_inventory_tonnes=actual_inv,
            mitigation_reductions_tonnes=gpt_tot,
            net_compliance_emissions_tonnes=net_emissions,
            quota_balance_tonnes=quota_balance,
            compliance_status=status,
            market_recommendation=rec,
        )

    @classmethod
    def generate_mitigation_summary(
        cls,
        facility_name: str,
        measures: List[MitigationMeasure],
        allocated_quota_tonnes: Optional[float] = None,
        actual_inventory_tonnes: Optional[float] = None,
        reporting_period: str = "2026",
    ) -> MitigationSummary:
        """Aggregate all mitigation measures and produce a regulatory summary (Mau 02 ND 06/2022)."""
        calculated_measures = [cls.calculate_measure(m) for m in measures]

        tot_ptcs = round(sum(m.baseline_emissions_ptcs for m in calculated_measures), 3)
        tot_pt = round(sum(m.actual_emissions_pt for m in calculated_measures), 3)
        tot_gpt = round(sum(m.emission_reduction_gpt for m in calculated_measures), 3)
        overall_pct = round((tot_gpt / tot_ptcs * 100.0), 2) if tot_ptcs > 0 else 0.0

        quota_profile = None
        if allocated_quota_tonnes is not None and actual_inventory_tonnes is not None:
            quota_profile = cls.calculate_quota_profile(
                facility_id="FAC-01",
                facility_name=facility_name,
                allocated_quota_tonnes=allocated_quota_tonnes,
                actual_inventory_tonnes=actual_inventory_tonnes,
                mitigation_reductions_tonnes=tot_gpt,
            )

        return MitigationSummary(
            facility_name=facility_name,
            reporting_period=reporting_period,
            total_baseline_ptcs=tot_ptcs,
            total_actual_pt=tot_pt,
            total_reduction_gpt=tot_gpt,
            overall_reduction_pct=overall_pct,
            measures=calculated_measures,
            quota_profile=quota_profile,
        )
