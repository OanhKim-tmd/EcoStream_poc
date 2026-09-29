"""SchemaDiscoveryAgent analyzing input documents, cataloging data sheets, and creating the task routing index."""

import time
from typing import Optional, List, Dict, Any
from ecostream.agents.base import BaseSubagent, AgentContext, AgentExecutionOutput
from ecostream.models.state import RunIndex, RoutingTask


class SchemaDiscoveryAgent(BaseSubagent):
    """Discovers document catalog, identifies corporate metadata, and assigns domain tasks."""

    def __init__(self, llm_client=None):
        super().__init__(name="SchemaDiscoveryAgent", llm_client=llm_client)

    def run(self, context: AgentContext, task: Optional[RoutingTask] = None) -> AgentExecutionOutput:
        start_time = time.time()
        discovered_tasks: List[RoutingTask] = []
        discovered_sources: List[str] = list(context.raw_markdown_sources.keys())

        # If LLM is available and not in offline mode, we can optionally use LLM to discover tasks
        if not context.offline_mode:
            llm_tasks = self._discover_with_llm(context)
            if llm_tasks:
                discovered_tasks = llm_tasks

        # Deterministic / rule-based discovery fallback
        if not discovered_tasks:
            discovered_tasks = self._discover_rule_based(context)

        # Build RunIndex
        run_index = RunIndex(
            run_id=context.run_id,
            company_name=context.company_name,
            facility_name=context.facility_name,
            reporting_year=context.reporting_year,
            discovered_sources=discovered_sources,
            tasks=discovered_tasks,
        )

        exec_time = time.time() - start_time
        return AgentExecutionOutput(
            agent_name=self.name,
            records=[],
            queries=[],
            assumptions=[],
            extra_data={"index": run_index.model_dump()},
            execution_time_sec=exec_time,
        )

    def _discover_rule_based(self, context: AgentContext) -> List[RoutingTask]:
        tasks: List[RoutingTask] = []
        task_counter = 1

        for source_name, content in context.raw_markdown_sources.items():
            content_lower = content.lower()

            # 1. Check for Scope 1 Fuel & Gas
            if any(k in content_lower for k in ["fuel", "diesel", "petrol", "xăng", "dầu", "lpg", "gas", "than", "coal", "đốt"]):
                tasks.append(
                    RoutingTask(
                        task_id=f"TASK-DISC-{task_counter:02d}",
                        target_agent="Scope1FuelAgent",
                        source_file=source_name,
                        domain="Scope 1 Direct Combustion",
                        description=f"Extract stationary and mobile fuel combustion data from {source_name}",
                        metadata={"source_name": source_name},
                    )
                )
                task_counter += 1

            # 2. Check for Scope 2 Electricity & EVN
            if any(k in content_lower for k in ["evn", "electricity", "điện", "kwh", "tiền điện", "công tơ", "trạm biến áp"]):
                tasks.append(
                    RoutingTask(
                        task_id=f"TASK-DISC-{task_counter:02d}",
                        target_agent="Scope2PowerAgent",
                        source_file=source_name,
                        domain="Scope 2 Purchased Electricity",
                        description=f"Extract purchased grid electricity and verify monthly continuity from {source_name}",
                        metadata={"source_name": source_name},
                    )
                )
                task_counter += 1

            # 3. Check for Scope 3 Supply Chain & Logistics
            if any(k in content_lower for k in ["freight", "logistics", "vận chuyển", "xe tải", "container", "tấn.km", "t.km", "carton", "bao bì", "vải", "cotton", "spend", "supplier", "mua hàng"]):
                tasks.append(
                    RoutingTask(
                        task_id=f"TASK-DISC-{task_counter:02d}",
                        target_agent="Scope3SupplyAgent",
                        source_file=source_name,
                        domain="Scope 3 Value Chain & Logistics",
                        description=f"Extract logistics freight and material procurement from {source_name}",
                        metadata={"source_name": source_name},
                    )
                )
                task_counter += 1

            # 4. Check for Mitigation & Quota Compliance (Mau 02)
            if any(k in content_lower for k in ["mitigation", "giảm nhẹ", "biện pháp", "quota", "hạn ngạch", "ptcs", "pt_cs", "mẫu 02", "nhiệt điện", "solar", "mái nhà", "biomass"]):
                tasks.append(
                    RoutingTask(
                        task_id=f"TASK-DISC-{task_counter:02d}",
                        target_agent="MitigationQuotaAgent",
                        source_file=source_name,
                        domain="Facility Mitigation & Quota Compliance",
                        description=f"Extract facility GHG reduction measures and quota allocation from {source_name}",
                        metadata={"source_name": source_name},
                    )
                )
                task_counter += 1

        return tasks

    def _discover_with_llm(self, context: AgentContext) -> List[RoutingTask]:
        sys_prompt = (
            "You are a GHG accounting schema discovery agent. Given document headers and summaries, "
            "categorize the data and create routing tasks for: Scope1FuelAgent, Scope2PowerAgent, "
            "Scope3SupplyAgent, and MitigationQuotaAgent. Return JSON: {'tasks': [{'task_id': '...', 'target_agent': '...', 'source_file': '...', 'domain': '...', 'description': '...'}]}"
        )
        sources_summary = "\n\n".join(
            [f"--- Source: {k} ---\n{v[:1500]}" for k, v in context.raw_markdown_sources.items()]
        )
        res = self.llm_client.generate_json(sys_prompt, sources_summary)
        if res and "tasks" in res:
            try:
                return [RoutingTask(**t) for t in res["tasks"]]
            except Exception:
                pass
        return []
