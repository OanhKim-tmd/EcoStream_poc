"""Multi-Agent Orchestrator coordinating domain subagents, blackboard state, deterministic math, and deliverables."""

import os
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from ecostream.ingestion.markitdown_loader import MarkItDownLoader
from ecostream.orchestrator.state import BlackboardWorkspace
from ecostream.privacy.pii_masker import PIIMasker, MaskMapping
import json
from ecostream.models.state import (
    RunState,
    PipelinePhase,
    AgentTaskResult,
    QueryLogEntry,
    AssumptionLogEntry,
)
from ecostream.models.activity import ActivityRecord
from ecostream.models.results import AuditReport, SMEInventorySummary
from ecostream.models.mitigation import MitigationSummary, MitigationMeasure

from ecostream.agents.base import AgentContext, LLMClient
from ecostream.agents.discovery import SchemaDiscoveryAgent
from ecostream.agents.scope1 import Scope1FuelAgent
from ecostream.agents.scope2 import Scope2PowerAgent
from ecostream.agents.scope3 import Scope3SupplyAgent
from ecostream.agents.mitigation import MitigationQuotaAgent
from ecostream.agents.synthesizer import ReportSynthesizerAgent

from ecostream.engine.calculator import CarbonCalculator
from ecostream.engine.reliability import ReliabilityEngine
from ecostream.engine.advisor import CarbonAdvisor
from ecostream.engine.mitigation_math import MitigationMathEngine
from ecostream.reporting.export import ReportExporter


class WorkflowOrchestrator:
    """Orchestrates the complete multi-agent lifecycle across the isolated run blackboard."""

    def __init__(
        self,
        run_id: Optional[str] = None,
        base_runs_dir: Optional[str] = None,
        llm_client: Optional[LLMClient] = None,
        offline_mode: bool = False,
    ):
        if run_id is None:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            run_id = f"run_{ts}"
        self.run_id = run_id
        self.workspace = BlackboardWorkspace(run_id, base_runs_dir)
        self.llm_client = llm_client or LLMClient()
        self.offline_mode = offline_mode or (os.environ.get("ECOSTREAM_OFFLINE_MODE") == "1")
        self.loader = MarkItDownLoader()

    def run_pipeline(
        self,
        input_files: List[str],
        company_name: str = "EcoGarment Vietnam JSC",
        facility_name: str = "Nhà máy May & Năng lượng Hà Nam",
        reporting_year: int = 2026,
    ) -> Dict[str, Any]:
        """Execute the complete end-to-end multi-agent pipeline."""
        # 1. Initialize
        state = self.workspace.initialize_workspace()
        state.phase = PipelinePhase.INGESTED
        state.progress_pct = 10.0
        self.workspace.save_state(state)

        # 2. Ingest & Convert Inputs to Markdown & PII Masking
        masker = PIIMasker()
        mapping = MaskMapping()
        
        # Mask provided corporate metadata
        masked_company = mapping.mask(company_name, "COMPANY")
        masked_facility = mapping.mask(facility_name, "FACILITY")

        raw_markdowns: Dict[str, str] = {}
        for fpath in input_files:
            if os.path.exists(fpath):
                self.workspace.store_raw_input(fpath)
                converted = self.loader.convert_file(fpath)
                # Store full workbook or separate sheets
                if converted.sheet_markdowns:
                    for sname, scontent in converted.sheet_markdowns.items():
                        md_fname = f"{os.path.splitext(converted.filename)[0]}_{sname}.md"
                        self.workspace.store_markdown_input(md_fname, scontent)
                        raw_markdowns[md_fname], mapping = masker.mask_text(scontent, mapping)
                else:
                    md_fname = f"{os.path.splitext(converted.filename)[0]}.md"
                    self.workspace.store_markdown_input(md_fname, converted.full_markdown)
                    raw_markdowns[md_fname], mapping = masker.mask_text(converted.full_markdown, mapping)

        context = AgentContext(
            run_id=self.run_id,
            company_name=masked_company,
            facility_name=masked_facility,
            reporting_year=reporting_year,
            raw_markdown_sources=raw_markdowns,
            offline_mode=self.offline_mode,
        )

        # 3. Schema Discovery & Indexing
        state.phase = PipelinePhase.INDEXED
        state.progress_pct = 25.0
        state.active_agent = "SchemaDiscoveryAgent"
        self.workspace.save_state(state)

        discovery_agent = SchemaDiscoveryAgent(llm_client=self.llm_client)
        discovery_out = discovery_agent.run(context)
        from ecostream.models.state import RunIndex
        
        idx_json = mapping.unmask_text(json.dumps(discovery_out.extra_data["index"]))
        run_index = RunIndex(**json.loads(idx_json))

        self.workspace.save_index(run_index)
        context.index = run_index

        state.agent_results["SchemaDiscoveryAgent"] = AgentTaskResult(
            agent_name="SchemaDiscoveryAgent",
            status="SUCCESS",
            execution_time_sec=discovery_out.execution_time_sec,
        )
        state.completed_tasks.append("SCHEMA_DISCOVERY")

        # 4. Domain Subagents Extraction
        state.phase = PipelinePhase.SUBAGENTS_EXTRACTING
        state.progress_pct = 40.0
        self.workspace.save_state(state)

        all_records: List[ActivityRecord] = []
        all_queries: List[QueryLogEntry] = []
        all_assumptions: List[AssumptionLogEntry] = []
        mitigation_data: Optional[Dict[str, Any]] = None

        domain_agents = [
            ("Scope1FuelAgent", Scope1FuelAgent(self.llm_client)),
            ("Scope2PowerAgent", Scope2PowerAgent(self.llm_client)),
        ]

        # In this PoC (per USTH_Inn 2026_EcoStream docx constraints):
        # "Phiên bản đầu chỉ tính CO₂ từ nhiên liệu tiêu thụ và điện mua vào...
        #  Phiên bản thử nghiệm không có chức năng dự báo, đề xuất giảm phát thải hoặc tính Scope 3."
        # So we skip Scope3 and Mitigation agents to strictly adhere to the project scope.

        for agent_name, agent_instance in domain_agents:
            state.active_agent = agent_name
            self.workspace.save_state(state)

            out = agent_instance.run(context)
            
            # Unmask outputs
            from ecostream.models.activity import ActivityRecord
            from ecostream.models.state import QueryLogEntry, AssumptionLogEntry
            
            if out.records:
                records_json = mapping.unmask_text(json.dumps([r.model_dump() for r in out.records]))
                unmasked_records = [ActivityRecord(**r) for r in json.loads(records_json)]
                out.records = unmasked_records
                all_records.extend(unmasked_records)
            
            if out.queries:
                queries_json = mapping.unmask_text(json.dumps([q.model_dump() for q in out.queries]))
                unmasked_queries = [QueryLogEntry(**q) for q in json.loads(queries_json)]
                out.queries = unmasked_queries
                all_queries.extend(unmasked_queries)
                
            if out.assumptions:
                assump_json = mapping.unmask_text(json.dumps([a.model_dump() for a in out.assumptions]))
                unmasked_assump = [AssumptionLogEntry(**a) for a in json.loads(assump_json)]
                out.assumptions = unmasked_assump
                all_assumptions.extend(unmasked_assump)


            if "mitigation_summary" in out.extra_data:
                mitigation_data = out.extra_data["mitigation_summary"]

            # Save intermediate per agent
            domain_prefixes = {
                "Scope1FuelAgent": "scope1",
                "Scope2PowerAgent": "scope2",
                "Scope3SupplyAgent": "scope3",
                "MitigationQuotaAgent": "mitigation",
            }
            prefix = domain_prefixes.get(agent_name, agent_name.lower().replace("agent", ""))
            if out.records:
                self.workspace.save_intermediate_json(f"{prefix}_extracted.json", out.records)
            elif "mitigation_summary" in out.extra_data:
                self.workspace.save_intermediate_json(f"{prefix}_extracted.json", out.extra_data["mitigation_summary"])

            state.agent_results[agent_name] = AgentTaskResult(
                agent_name=agent_name,
                status="SUCCESS",
                extracted_count=len(out.records),
                queries_raised=len(out.queries),
                assumptions_made=len(out.assumptions),
                output_file=f"{prefix}_extracted.json",
                execution_time_sec=out.execution_time_sec,
            )
            state.completed_tasks.append(agent_name)

        # Save query log and assumption log
        
        # Save mapping
        with open(os.path.join(self.workspace.run_dir, "pii_mapping.json"), "w", encoding="utf-8") as f:
            f.write(mapping.to_json())
        self.workspace.save_intermediate_json("query_log.json", all_queries)
        self.workspace.save_intermediate_json("assumption_log.json", all_assumptions)

        # 5. Deterministic Python Math Engine
        state.phase = PipelinePhase.CALCULATING
        state.progress_pct = 70.0
        state.active_agent = "PythonMathEngine"
        self.workspace.save_state(state)

        calculator = CarbonCalculator()
        calculations = calculator.calculate_all(all_records)
        scope_breakdowns, total_tonnes, total_min, total_max = calculator.aggregate_scopes(calculations)

        # Calculate assumption penalty
        total_penalty = min(25.0, sum(a.confidence_penalty * 100.0 for a in all_assumptions))
        reliability = ReliabilityEngine.evaluate(all_records, assumption_penalty=total_penalty)

        # Mitigation Summary is skipped in this PoC mode per instructions
        mitigation_summary = None
        # if mitigation_data:
        #     measures = [MitigationMeasure(**m) for m in mitigation_data.get("measures", [])]
        #     mitigation_summary = MitigationMathEngine.generate_mitigation_summary(
        #         facility_name=facility_name,
        #         measures=measures,
        #         allocated_quota_tonnes=4000.0,
        #         actual_inventory_tonnes=total_tonnes,
        #         reporting_period=str(reporting_year),
        #     )
        #     self.workspace.save_intermediate_json("mitigation_summary.json", mitigation_summary)

        inventory_summary = CarbonAdvisor.compile_summary(
            company_name=company_name,
            facility_location=facility_name,
            reporting_period=str(reporting_year),
            industry_sector="May mặc & Công nghiệp phụ trợ",
            records=all_records,
            calculations=calculations,
            scopes=scope_breakdowns,
            total_tonnes=total_tonnes,
            total_min=total_min,
            total_max=total_max,
            reliability=reliability,
        )

        math_results = {
            "total_co2e_tonnes": total_tonnes,
            "uncertainty_min": total_min,
            "uncertainty_max": total_max,
            "reliability_score": reliability.overall_confidence_score,
            "grade": reliability.grade,
            "calculations_count": len(calculations),
            "scopes": [s.model_dump() for s in scope_breakdowns],
        }
        self.workspace.save_intermediate_json("math_results.json", math_results)

        # 6. Report Synthesis & Deliverables Export
        state.phase = PipelinePhase.SYNTHESIZING
        state.progress_pct = 85.0
        state.active_agent = "ReportSynthesizerAgent"
        self.workspace.save_state(state)

        synth_agent = ReportSynthesizerAgent(self.llm_client)
        synth_out = synth_agent.run(context)

        audit_report = AuditReport(
            report_id=f"AUDIT-{self.run_id}",
            generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            summary=inventory_summary,
            calculations=calculations,
            mitigation_summary=mitigation_summary,
            queries=all_queries,
            assumptions=all_assumptions,
        )

        # Generate Deliverable Files
        deliv_dir = self.workspace.deliverables_dir
        # JSON summary
        json_path = os.path.join(deliv_dir, "final_inventory_summary.json")
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(audit_report.model_dump_json(indent=2))

        # Markdown Report
        md_content = ReportExporter.to_markdown(audit_report)
        md_path = os.path.join(deliv_dir, "Bao_cao_kiem_ke_va_giam_nhe_KNK.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        # Standalone HTML Report
        html_content = ReportExporter.to_html(audit_report)
        html_path = os.path.join(deliv_dir, "Bao_cao_kiem_ke_va_giam_nhe_KNK.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Word Report (.docx)
        docx_path = os.path.join(deliv_dir, "Bao_cao_Mau02_ND06.docx")
        try:
            docx_bytes = ReportExporter.to_docx(audit_report)
            with open(docx_path, "wb") as f:
                f.write(docx_bytes)
        except Exception as e:
            print(f"Notice: DOCX generation skipped ({e})")

        # PDF Report
        pdf_path = os.path.join(deliv_dir, "Bao_cao_kiem_ke_va_giam_nhe_KNK.pdf")
        try:
            pdf_bytes = ReportExporter.to_pdf(audit_report)
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)
        except Exception as e:
            print(f"Notice: PDF generation skipped ({e})")

        # Excel Report (New EcoStream requirement)
        excel_path = os.path.join(deliv_dir, "Ho_so_ket_qua_CO2_EcoStream.xlsx")
        try:
            ReportExporter.to_excel(audit_report, excel_path)
        except Exception as e:
            print(f"Notice: Excel generation failed ({e})")

        # 7. Finalize State
        state.phase = PipelinePhase.COMPLETED
        state.progress_pct = 100.0
        state.active_agent = None
        state.end_time = datetime.now(timezone.utc).isoformat()
        self.workspace.save_state(state)

        return {
            "run_id": self.run_id,
            "status": "COMPLETED",
            "summary": inventory_summary.model_dump(),
            "mitigation_summary": mitigation_summary.model_dump() if mitigation_summary else None,
            "queries": [q.model_dump() for q in all_queries],
            "assumptions": [a.model_dump() for a in all_assumptions],
            "deliverables": {
                "json": json_path,
                "markdown": md_path,
                "html": html_path,
                "docx": docx_path,
                "pdf": pdf_path,
                "excel": excel_path,
                "run_dir": self.workspace.run_dir,
            },
        }
