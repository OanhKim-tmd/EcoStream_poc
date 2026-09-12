"""Domain models for calculation results, reliability scores, and inventory summaries."""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from ecostream.models.activity import EmissionScope, ActivityCategory, EvidenceProvenance


class CarbonCalculation(BaseModel):
    """Calculated GHG emission result with traceable factor matching and uncertainty bounds."""
    activity_id: str
    description: str
    scope: EmissionScope
    category: ActivityCategory
    activity_value: float
    activity_unit: str
    emission_factor_value: float
    emission_factor_unit: str
    emission_factor_source: str
    co2e_kg: float
    co2e_tonnes: float
    uncertainty_pct: float = Field(description="Uncertainty percentage (+/- %)")
    uncertainty_min_tonnes: float
    uncertainty_max_tonnes: float
    quality_composite_score: float
    evidence: EvidenceProvenance


class DimensionScore(BaseModel):
    """Evaluation of a specific reliability dimension (0-100%)."""
    name: str
    score: float
    grade: str
    explanation: str


class ReliabilityAssessment(BaseModel):
    """Overall EcoStream Confidence Index and dimensional evaluations."""
    overall_confidence_score: float = Field(ge=0.0, le=100.0)
    grade: str = Field(description="A (Audit-Ready), B (Fair), C (Needs Improvement), D (High Risk)")
    grade_label: str
    summary_verdict: str
    dimensions: Dict[str, DimensionScore]
    spend_based_ratio_pct: float
    primary_data_ratio_pct: float


class ReductionRecommendation(BaseModel):
    """Actionable recommendation for SME to upgrade data quality or reduce emissions."""
    id: str
    title: str
    priority: str = Field(description="HIGH, MEDIUM, or LOW")
    category: str
    current_gap: str
    action_required: str
    potential_confidence_gain_pct: float
    target_scope: EmissionScope
    affected_item_ids: List[str] = Field(default_factory=list)


class ScopeBreakdown(BaseModel):
    """Consolidated emissions and uncertainty per GHG Scope."""
    scope: EmissionScope
    total_tonnes: float
    percentage: float
    uncertainty_lower_tonnes: float
    uncertainty_upper_tonnes: float
    activity_count: int
    avg_confidence_pct: float


class SMEInventorySummary(BaseModel):
    """Executive carbon inventory overview for an SME."""
    company_name: str
    facility_location: str
    reporting_period: str
    industry_sector: str
    total_co2e_tonnes: float
    total_uncertainty_min_tonnes: float
    total_uncertainty_max_tonnes: float
    scope_1_tonnes: float
    scope_2_tonnes: float
    scope_3_tonnes: float
    scopes: List[ScopeBreakdown]
    reliability: ReliabilityAssessment
    hotspots: List[CarbonCalculation]
    recommendations: List[ReductionRecommendation]


class AuditReport(BaseModel):
    """Comprehensive exportable audit payload."""
    report_id: str
    generated_at: str
    summary: SMEInventorySummary
    calculations: List[CarbonCalculation]
