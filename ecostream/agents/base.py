"""Base subagent abstractions, LLM client connector, and agent context."""

import os
import json
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type, TypeVar
from pydantic import BaseModel, Field

from ecostream.models.activity import ActivityRecord
from ecostream.models.state import QueryLogEntry, AssumptionLogEntry, RunIndex, RoutingTask

T = TypeVar("T", bound=BaseModel)


class AgentContext(BaseModel):
    """Execution context and reference data passed to domain subagents."""
    run_id: str
    company_name: str = "EcoGarment Vietnam JSC"
    facility_name: Optional[str] = "Nhà máy May & Năng lượng Hà Nam"
    reporting_year: int = 2026
    raw_markdown_sources: Dict[str, str] = Field(default_factory=dict)
    reference_markdowns: Dict[str, str] = Field(default_factory=dict)
    index: Optional[RunIndex] = None
    offline_mode: bool = True


class AgentExecutionOutput(BaseModel):
    """Standardized output produced by a domain subagent."""
    agent_name: str
    records: List[ActivityRecord] = Field(default_factory=list)
    queries: List[QueryLogEntry] = Field(default_factory=list)
    assumptions: List[AssumptionLogEntry] = Field(default_factory=list)
    extra_data: Dict[str, Any] = Field(default_factory=dict)
    execution_time_sec: float = 0.0


class LLMClient:
    """Connector for LLM API endpoints with structured JSON output and fallback resilience."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: str = "qwen2.5:7b",
        timeout: float = 30.0,
    ):
        # Default to local-first Ollama / vLLM on-premise endpoint
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1"))
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", os.environ.get("OLLAMA_API_KEY", "local-token"))
        self.model = os.environ.get("LLM_MODEL", model)
        self.timeout = timeout

    def generate_json(self, system_prompt: str, user_prompt: str, max_retries: int = 2) -> Optional[Dict[str, Any]]:
        """Call LLM endpoint and enforce valid JSON output."""
        try:
            import httpx

            url = f"{self.base_url.rstrip('/')}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.0,
            }

            for attempt in range(max_retries + 1):
                try:
                    resp = httpx.post(url, headers=headers, json=payload, timeout=self.timeout)
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data["choices"][0]["message"]["content"]
                        return json.loads(content)
                except Exception as e:
                    if attempt == max_retries:
                        print(f"Notice: LLM call to {url} skipped/failed ({e})")
                        break
                    time.sleep(1.0)
        except Exception as e:
            print(f"Notice: LLM HTTP client unavailable ({e})")
        return None


class BaseSubagent(ABC):
    """Abstract domain subagent."""

    def __init__(self, name: str, llm_client: Optional[LLMClient] = None):
        self.name = name
        self.llm_client = llm_client or LLMClient()

    @abstractmethod
    def run(self, context: AgentContext, task: Optional[RoutingTask] = None) -> AgentExecutionOutput:
        """Execute domain extraction and reasoning."""
        pass
