"""End-to-end tests for Multi-Agent Workflow Orchestrator on multi-sheet benchmark input.xlsx."""

import os
import shutil
import unittest
from ecostream.orchestrator.pipeline import WorkflowOrchestrator
from ecostream.models.state import PipelinePhase
from scripts.generate_mock_excel import generate_benchmark_excel


class TestOrchestratorE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_excel = "data/samples/test_input.xlsx"
        generate_benchmark_excel(cls.test_excel)
        cls.run_id = "test_run_orchestrator_e2e"
        cls.test_runs_dir = "runs_test"
        if os.path.exists(cls.test_runs_dir):
            shutil.rmtree(cls.test_runs_dir, ignore_errors=True)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_excel):
            os.remove(cls.test_excel)
        if os.path.exists(cls.test_runs_dir):
            shutil.rmtree(cls.test_runs_dir, ignore_errors=True)

    def test_full_pipeline_execution(self):
        orchestrator = WorkflowOrchestrator(
            run_id=self.run_id,
            base_runs_dir=self.test_runs_dir,
            offline_mode=True,
        )

        result = orchestrator.run_pipeline(
            input_files=[self.test_excel],
            company_name="EcoGarment Vietnam JSC",
            facility_name="Nhà máy May & Năng lượng Hà Nam",
            reporting_year=2026,
        )

        # 1. Pipeline Completion
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["run_id"], self.run_id)

        # 2. State & Index artifacts
        state = orchestrator.workspace.load_state()
        self.assertIsNotNone(state)
        self.assertEqual(state.phase, PipelinePhase.COMPLETED)
        self.assertEqual(state.progress_pct, 100.0)
        self.assertIn("SchemaDiscoveryAgent", state.agent_results)
        self.assertIn("Scope1FuelAgent", state.agent_results)
        self.assertIn("Scope2PowerAgent", state.agent_results)
        self.assertIn("Scope3SupplyAgent", state.agent_results)
        self.assertIn("MitigationQuotaAgent", state.agent_results)

        run_index = orchestrator.workspace.load_index()
        self.assertIsNotNone(run_index)
        self.assertGreater(len(run_index.routing_tasks), 0)

        # 3. Intermediates verification
        scope1_data = orchestrator.workspace.load_intermediate_json("scope1_extracted.json")
        self.assertIsNotNone(scope1_data)
        self.assertGreater(len(scope1_data), 0)

        scope2_data = orchestrator.workspace.load_intermediate_json("scope2_extracted.json")
        self.assertIsNotNone(scope2_data)
        self.assertGreaterEqual(len(scope2_data), 11)  # All 12 months (11 original + 1 interpolated July)

        query_log = orchestrator.workspace.load_intermediate_json("query_log.json")
        self.assertIsNotNone(query_log)
        self.assertGreaterEqual(len(query_log), 3)  # LPG unit, EVN July missing, Spend proxy

        assumption_log = orchestrator.workspace.load_intermediate_json("assumption_log.json")
        self.assertIsNotNone(assumption_log)
        self.assertGreaterEqual(len(assumption_log), 3)

        math_results = orchestrator.workspace.load_intermediate_json("math_results.json")
        self.assertIsNotNone(math_results)
        self.assertGreater(math_results["total_co2e_tonnes"], 0.0)
        self.assertLess(math_results["uncertainty_min"], math_results["total_co2e_tonnes"])
        self.assertGreater(math_results["uncertainty_max"], math_results["total_co2e_tonnes"])

        # 4. Mitigation Summary (Mau 02 ND 06/2022)
        mitigation_summary = orchestrator.workspace.load_intermediate_json("mitigation_summary.json")
        self.assertIsNotNone(mitigation_summary)
        self.assertGreater(mitigation_summary["total_baseline_ptcs"], 0.0)
        self.assertGreater(mitigation_summary["total_actual_pt"], 0.0)
        self.assertGreater(mitigation_summary["total_reduction_gpt"], 0.0)
        self.assertIn("quota_profile", mitigation_summary)

        # 5. Deliverables generated
        deliv_files = os.listdir(orchestrator.workspace.deliverables_dir)
        self.assertIn("final_inventory_summary.json", deliv_files)
        self.assertIn("Bao_cao_kiem_ke_va_giam_nhe_KNK.md", deliv_files)
        self.assertIn("Bao_cao_kiem_ke_va_giam_nhe_KNK.html", deliv_files)

        # Verify Markdown content
        md_file = os.path.join(orchestrator.workspace.deliverables_dir, "Bao_cao_kiem_ke_va_giam_nhe_KNK.md")
        with open(md_file, "r", encoding="utf-8") as f:
            md_text = f.read()
            self.assertIn("BÁO CÁO KIỂM KÊ", md_text)
            self.assertIn("EcoGarment Vietnam JSC", md_text)


if __name__ == "__main__":
    unittest.main()
