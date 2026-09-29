"""Domain subagents for multi-agent GHG carbon accounting and audit workflow."""

from ecostream.agents.base import (
    BaseSubagent,
    AgentContext,
    AgentExecutionOutput,
    LLMClient,
)
from ecostream.agents.discovery import SchemaDiscoveryAgent
from ecostream.agents.scope1 import Scope1FuelAgent
from ecostream.agents.scope2 import Scope2PowerAgent
from ecostream.agents.scope3 import Scope3SupplyAgent
from ecostream.agents.mitigation import MitigationQuotaAgent
from ecostream.agents.synthesizer import ReportSynthesizerAgent

__all__ = [
    "BaseSubagent",
    "AgentContext",
    "AgentExecutionOutput",
    "LLMClient",
    "SchemaDiscoveryAgent",
    "Scope1FuelAgent",
    "Scope2PowerAgent",
    "Scope3SupplyAgent",
    "MitigationQuotaAgent",
    "ReportSynthesizerAgent",
]
