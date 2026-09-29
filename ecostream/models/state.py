"""State management, query log, assumption log, and agent routing models."""

from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class PipelinePhase(str, Enum):
    INITIALIZED = "INITIALIZED"
    INGESTED = "INGESTED"
    INDEXED = "INDEXED"
    SUBAGENTS_EXTRACTING = "SUBAGENTS_EXTRACTING"
    CALCULATING = "CALCULATING"
    SYNTHESIZING = "SYNTHESIZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class RoutingTask(BaseModel):
    """Task assigned by SchemaDiscoveryAgent to a domain subagent."""
    task_id: str
    target_agent: str = Field(description="Scope1FuelAgent, Scope2PowerAgent, Scope3SupplyAgent, MitigationQuotaAgent")
    source_file: str
    sheet_name: Optional[str] = None
    domain: str
    description: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RunIndex(BaseModel):
    """Data catalog and routing index produced by SchemaDiscoveryAgent."""
    run_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    company_name: str = "EcoGarment Vietnam JSC"
    facility_name: Optional[str] = "Nhà máy May & Năng lượng Hà Nam"
    reporting_year: Optional[int] = 2026
    discovered_sources: List[str] = Field(default_factory=list)
    tasks: List[RoutingTask] = Field(default_factory=list)

    @property
    def routing_tasks(self) -> List[RoutingTask]:
        return self.tasks



class QueryStatus(str, Enum):
    OPEN = "OPEN"
    AUTO_ASSUMED = "AUTO_ASSUMED"
    RESOLVED = "RESOLVED"
    FLAGGED = "FLAGGED"


class AnomalyType(str, Enum):
    MISSING_VALUE = "MISSING_VALUE"
    UNIT_AMBIGUITY = "UNIT_AMBIGUITY"
    OUTLIER = "OUTLIER"
    SPEND_PROXY = "SPEND_PROXY"
    SEASONAL_GAP = "SEASONAL_GAP"
    CLASSIFICATION_UNCERTAINTY = "CLASSIFICATION_UNCERTAINTY"


class QueryLogEntry(BaseModel):
    """Asynchronous audit query logged when an anomaly or gap is spotted."""
    query_id: str
    scope: str = Field(description="Scope 1, Scope 2, Scope 3, Mitigation")
    field_name: str
    anomaly_type: AnomalyType
    source_reference: str = Field(description="File, sheet, row, or invoice snippet")
    detected_issue: str
    action_taken: str = Field(description="Non-blocking conservative assumption applied")
    suggested_human_action: str = Field(description="Suggested document upload or confirmation")
    status: QueryStatus = QueryStatus.AUTO_ASSUMED
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AssumptionLogEntry(BaseModel):
    """Explicit assumption applied by subagents with confidence penalty and uncertainty markup."""
    assumption_id: str
    related_query_id: Optional[str] = None
    parameter_name: str
    assumed_value: Any
    assumed_unit: str
    justification: str
    confidence_penalty: float = Field(default=0.10, ge=0.0, le=1.0, description="Deduction from data quality score")
    uncertainty_markup_pct: float = Field(default=15.0, description="Additional uncertainty percentage markup")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AgentTaskResult(BaseModel):
    """Summary of execution result from a domain subagent."""
    agent_name: str
    status: str = "SUCCESS"
    extracted_count: int = 0
    queries_raised: int = 0
    assumptions_made: int = 0
    output_file: str = ""
    execution_time_sec: float = 0.0


class RunState(BaseModel):
    """Blackboard lifecycle state of a pipeline execution run."""
    run_id: str
    phase: PipelinePhase = PipelinePhase.INITIALIZED
    progress_pct: float = 0.0
    start_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    end_time: Optional[str] = None
    active_agent: Optional[str] = None
    completed_tasks: List[str] = Field(default_factory=list)
    agent_results: Dict[str, AgentTaskResult] = Field(default_factory=dict)
    error_message: Optional[str] = None
