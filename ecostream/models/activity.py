"""Core domain models for greenhouse gas activity records and provenance."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class EmissionScope(str, Enum):
    SCOPE_1 = "Scope 1"  # Direct emissions (fuel combustion, company fleet, generators)
    SCOPE_2 = "Scope 2"  # Indirect emissions (purchased electricity from grid)
    SCOPE_3 = "Scope 3"  # Value chain emissions (freight, materials, packaging)


class ActivityCategory(str, Enum):
    STATIONARY_COMBUSTION = "Stationary Combustion"
    MOBILE_COMBUSTION = "Mobile Combustion"
    PURCHASED_ELECTRICITY = "Purchased Electricity"
    UPSTREAM_TRANSPORTATION = "Upstream Transportation & Logistics"
    PURCHASED_GOODS = "Purchased Goods & Packaging"
    WASTE = "Waste Generated in Operations"


class MeasurementType(str, Enum):
    PRIMARY_METERED = "Primary Metered"          # Direct meter reading (highest accuracy)
    PRIMARY_INVOICED = "Primary Invoiced"        # Certified VAT e-invoice (EVN / Petrolimex)
    ESTIMATED_ACTIVITY = "Estimated Activity"    # Route/load distance calculation
    SPEND_BASED_PROXY = "Spend-Based Proxy"      # Financial proxy (lowest reliability)


class EvidenceProvenance(BaseModel):
    """Audit trail linking extracted activity data back to the original source document."""
    source_document: str = Field(description="Name of source file or upload")
    document_type: str = Field(description="Type of document, e.g. EVN_BILL, FUEL_INVOICE, FREIGHT_LOG, EXCEL_LEDGER")
    page_or_line: Optional[str] = Field(default=None, description="Page or line number in the source")
    snippet: str = Field(description="Exact raw excerpt or table line extracted from source")
    extraction_method: str = Field(default="RULE_BASED", description="Extraction engine used (RULE_BASED, REGEX, LLM)")
    extraction_confidence: float = Field(default=0.95, ge=0.0, le=1.0, description="Confidence of text extraction")


class DataQualityIndicator(BaseModel):
    """5-dimensional data quality assessment following GHG Protocol / EcoStream criteria."""
    completeness_score: float = Field(ge=0.0, le=1.0, description="Completeness of metadata and parameters")
    temporal_score: float = Field(ge=0.0, le=1.0, description="Temporal alignment to the reporting year/month")
    geographical_score: float = Field(ge=0.0, le=1.0, description="Geographic specificity (Vietnam local vs global)")
    source_reliability_score: float = Field(ge=0.0, le=1.0, description="Reliability tier of the measurement method")
    extraction_confidence_score: float = Field(ge=0.0, le=1.0, description="Extraction certainty from raw document")

    @property
    def composite_score(self) -> float:
        """Weighted EcoStream reliability score (0.0 - 1.0)."""
        return round(
            0.25 * self.completeness_score
            + 0.15 * self.temporal_score
            + 0.20 * self.geographical_score
            + 0.25 * self.source_reliability_score
            + 0.15 * self.extraction_confidence_score,
            4,
        )


class ActivityRecord(BaseModel):
    """Normalized activity record ready for emission factor lookup and calculation."""
    id: str
    description: str
    scope: EmissionScope
    category: ActivityCategory
    quantity: float
    unit: str
    date: Optional[str] = None
    supplier: Optional[str] = None
    cost_vnd: Optional[float] = None
    measurement_type: MeasurementType
    evidence: EvidenceProvenance
    quality: DataQualityIndicator
