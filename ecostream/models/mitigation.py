"""Facility-level GHG Mitigation & Quota Compliance models according to Decree 06/2022/ND-CP (amended by Decree 119/2025/ND-CP)."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class MitigationCategory(str, Enum):
    RENEWABLE_ENERGY = "RENEWABLE_ENERGY"
    ENERGY_EFFICIENCY = "ENERGY_EFFICIENCY"
    FUEL_SWITCHING = "FUEL_SWITCHING"
    WASTE_HEAT_RECOVERY = "WASTE_HEAT_RECOVERY"
    TECHNOLOGY_UPGRADE = "TECHNOLOGY_UPGRADE"
    PROCESS_OPTIMIZATION = "PROCESS_OPTIMIZATION"


class MitigationMeasure(BaseModel):
    """Specific greenhouse gas mitigation measure implemented at a facility."""
    measure_id: str
    measure_name: str
    category: MitigationCategory = MitigationCategory.ENERGY_EFFICIENCY
    start_date: Optional[str] = None
    description: str
    baseline_emissions_ptcs: float = Field(description="Mức phát thải dự kiến / kịch bản cơ sở (PT_CS) in tCO2e")
    actual_emissions_pt: float = Field(description="Mức phát thải thực tế sau biện pháp (PT) in tCO2e")
    emission_reduction_gpt: float = Field(description="Lượng giảm phát thải GPT = PT_CS - PT in tCO2e")
    reduction_pct: float = Field(default=0.0, description="Tỷ lệ giảm phát thải %")
    monitoring_method: str = Field(default="Đo đếm trực tiếp theo Phương án giám sát đã duyệt")
    uncertainty_pct: float = Field(default=5.0, description="Độ không chắc chắn +/- %")
    evidence_source: str = Field(default="Nhật ký vận hành & Biên bản nghiệm thu")


class FacilityQuotaProfile(BaseModel):
    """Facility emission quota allocation and compliance balance under Decree 06/2022 and Decree 119/2025."""
    facility_id: str
    facility_name: str
    decision_ref: str = "Quyết định 42/2026/QĐ-TTg & NĐ 119/2025/NĐ-CP"
    reporting_year: int = 2026
    allocated_quota_tonnes: float = Field(description="Hạn ngạch phát thải được phân bổ (tCO2e)")
    actual_inventory_tonnes: float = Field(description="Tổng phát thải kiểm kê thực tế của cơ sở (tCO2e)")
    mitigation_reductions_tonnes: float = Field(default=0.0, description="Tổng lượng giảm phát thải từ các biện pháp (GPT_total in tCO2e)")
    net_compliance_emissions_tonnes: float = Field(description="Mức phát thải tính tuân thủ sau giảm nhẹ (tCO2e)")
    quota_balance_tonnes: float = Field(description="Chênh lệch hạn ngạch = Hạn ngạch phân bổ - Phát thải tuân thủ (tCO2e)")
    compliance_status: str = Field(description="THẶNG DƯ (SURPLUS) hoặc THIẾU HỤT (DEFICIT)")
    market_recommendation: str = Field(description="Khuyến nghị tham gia sàn giao dịch carbon / bù trừ")


class MitigationSummary(BaseModel):
    """Aggregated facility mitigation and quota compliance disclosure (Mau 02 ND 06/2022)."""
    facility_name: str
    reporting_period: str = "2026"
    total_baseline_ptcs: float
    total_actual_pt: float
    total_reduction_gpt: float
    overall_reduction_pct: float
    measures: List[MitigationMeasure] = Field(default_factory=list)
    quota_profile: Optional[FacilityQuotaProfile] = None
