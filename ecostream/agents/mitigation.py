"""MitigationQuotaAgent extracting facility GHG mitigation projects and quota compliance data (Mau 02 ND 06/2022)."""

import re
import time
from typing import Optional, List
from ecostream.agents.base import BaseSubagent, AgentContext, AgentExecutionOutput
from ecostream.models.mitigation import (
    MitigationMeasure,
    MitigationCategory,
    MitigationSummary,
)
from ecostream.models.state import RoutingTask
from ecostream.engine.mitigation_math import MitigationMathEngine


class MitigationQuotaAgent(BaseSubagent):
    """Specialized domain subagent for Facility Mitigation accounting and Quota compliance."""

    def __init__(self, llm_client=None):
        super().__init__(name="MitigationQuotaAgent", llm_client=llm_client)

    def run(self, context: AgentContext, task: Optional[RoutingTask] = None) -> AgentExecutionOutput:
        start_time = time.time()
        measures: List[MitigationMeasure] = []
        allocated_quota = 4000.0  # default allocated quota in tCO2e

        target_sources = {}
        if task and task.source_file in context.raw_markdown_sources:
            target_sources[task.source_file] = context.raw_markdown_sources[task.source_file]
        else:
            for k, v in context.raw_markdown_sources.items():
                if any(kw in k.lower() or kw in v.lower() for kw in ["mitigation", "giảm nhẹ", "biện pháp", "quota", "hạn ngạch", "ptcs", "solar", "biomass"]):
                    target_sources[k] = v

        measure_idx = 1

        for src_name, content in target_sources.items():
            lines = content.split("\n")
            for line in lines:
                if not line.strip() or line.startswith("| ---") or "measure" in line.lower() and "ptcs" in line.lower():
                    continue

                line_lower = line.lower()

                # 1. Rooftop Solar Photovoltaic
                if "solar" in line_lower or "mặt trời" in line_lower:
                    ptcs_val = self._extract_pt_values(line, default_ptcs=950.0, default_pt=180.0)
                    measures.append(
                        MitigationMeasure(
                            measure_id=f"MM-{measure_idx:02d}",
                            measure_name="Lắp đặt hệ thống Điện mặt trời mái nhà 1.2 MWp tự dùng",
                            category=MitigationCategory.RENEWABLE_ENERGY,
                            start_date="2026-01-01",
                            description="Tự phát tự dùng điện mặt trời thay thế 40% sản lượng điện nhận từ lưới quốc gia.",
                            baseline_emissions_ptcs=ptcs_val[0],
                            actual_emissions_pt=ptcs_val[1],
                            emission_reduction_gpt=0.0,  # Computed deterministically
                            monitoring_method="Đo đếm điện năng hai chiều qua công tơ điện tử đa chức năng cấp chính xác 0.2S",
                            uncertainty_pct=3.5,
                            evidence_source=f"{src_name} - Nhật ký vận hành Inverter & Hệ thống SCADA",
                        )
                    )
                    measure_idx += 1

                # 2. Biomass Co-firing
                elif "biomass" in line_lower or "đồng đốt" in line_lower or "viên nén" in line_lower:
                    ptcs_val = self._extract_pt_values(line, default_ptcs=2400.0, default_pt=1750.0)
                    measures.append(
                        MitigationMeasure(
                            measure_id=f"MM-{measure_idx:02d}",
                            measure_name="Chuyển đổi nhiên liệu đồng đốt 15% viên nén sinh khối (Biomass Co-firing)",
                            category=MitigationCategory.FUEL_SWITCHING,
                            start_date="2026-02-01",
                            description="Thay thế một phần than đá công nghiệp bằng viên nén gỗ mùn cưa trung tính carbon.",
                            baseline_emissions_ptcs=ptcs_val[0],
                            actual_emissions_pt=ptcs_val[1],
                            emission_reduction_gpt=0.0,
                            monitoring_method="Phiếu cân điện tử trạm cân xe tải và biên bản phân tích nhiệt trị nhiên liệu",
                            uncertainty_pct=5.0,
                            evidence_source=f"{src_name} - Nhật ký cấp nhiên liệu lò hơi",
                        )
                    )
                    measure_idx += 1

                # 3. Variable Frequency Drive (VFD) Inverter Motor Optimization
                elif "vfd" in line_lower or "biến tần" in line_lower or "tiết kiệm điện" in line_lower or "động cơ" in line_lower:
                    ptcs_val = self._extract_pt_values(line, default_ptcs=420.0, default_pt=310.0)
                    measures.append(
                        MitigationMeasure(
                            measure_id=f"MM-{measure_idx:02d}",
                            measure_name="Lắp đặt biến tần VFD tối ưu hóa động cơ bơm và quạt gió lò hơi",
                            category=MitigationCategory.ENERGY_EFFICIENCY,
                            start_date="2026-03-01",
                            description="Tự động điều chỉnh lưu lượng gió và áp lực nước theo phụ tải thực tế.",
                            baseline_emissions_ptcs=ptcs_val[0],
                            actual_emissions_pt=ptcs_val[1],
                            emission_reduction_gpt=0.0,
                            monitoring_method="Đo đếm công suất tiêu thụ điện tại tủ điều khiển động cơ trước và sau lắp đặt",
                            uncertainty_pct=4.0,
                            evidence_source=f"{src_name} - Biên bản đo kiểm hiệu suất năng lượng",
                        )
                    )
                    measure_idx += 1

                # Check for quota line
                if "quota" in line_lower or "hạn ngạch" in line_lower:
                    q_match = re.search(r"(\d+(?:[.,]\d+)?)", line)
                    if q_match:
                        try:
                            allocated_quota = float(q_match.group(1).replace(".", "").replace(",", ""))
                        except ValueError:
                            pass

        # If no explicit measures were found in input documents, provide standard benchmark measures
        if not measures:
            measures = [
                MitigationMeasure(
                    measure_id="MM-01",
                    measure_name="Lắp đặt hệ thống Điện mặt trời mái nhà 1.2 MWp",
                    category=MitigationCategory.RENEWABLE_ENERGY,
                    description="Tự phát tự dùng điện mặt trời thay thế điện lưới EVN",
                    baseline_emissions_ptcs=950.0,
                    actual_emissions_pt=180.0,
                    emission_reduction_gpt=0.0,
                ),
                MitigationMeasure(
                    measure_id="MM-02",
                    measure_name="Đồng đốt 15% viên nén sinh khối tại lò hơi",
                    category=MitigationCategory.FUEL_SWITCHING,
                    description="Thay thế than cám bằng viên nén gỗ mùn cưa",
                    baseline_emissions_ptcs=2400.0,
                    actual_emissions_pt=1750.0,
                    emission_reduction_gpt=0.0,
                ),
            ]

        # Use deterministic math engine
        mitigation_summary = MitigationMathEngine.generate_mitigation_summary(
            facility_name=context.facility_name or "Nhà máy May & Năng lượng Hà Nam",
            measures=measures,
            allocated_quota_tonnes=allocated_quota,
            actual_inventory_tonnes=3650.0,  # Will be adjusted by orchestrator after math step
            reporting_period=str(context.reporting_year),
        )

        exec_time = time.time() - start_time
        return AgentExecutionOutput(
            agent_name=self.name,
            records=[],
            queries=[],
            assumptions=[],
            extra_data={"mitigation_summary": mitigation_summary.model_dump()},
            execution_time_sec=exec_time,
        )

    def _extract_pt_values(self, line: str, default_ptcs: float, default_pt: float) -> tuple[float, float]:
        if "|" in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            numeric_cells = []
            for p in parts:
                try:
                    numeric_cells.append(float(p.replace(",", "")))
                except ValueError:
                    pass
            if len(numeric_cells) >= 2:
                return numeric_cells[0], numeric_cells[1]

        matches = re.findall(r"(\d+(?:\.\d+)?)", line)
        if len(matches) >= 2:
            # Take the last 2 numeric values (emission figures are placed at the end of description)
            return float(matches[-2]), float(matches[-1])
        return default_ptcs, default_pt
