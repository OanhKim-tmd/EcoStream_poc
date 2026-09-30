"""Unit and integration tests for EcoStream Live Monitor API endpoints."""

import os
import unittest
from starlette.testclient import TestClient
from ecostream.app.server import app, RUNS_DIR
from ecostream.orchestrator.pipeline import WorkflowOrchestrator
from ecostream.orchestrator.state import BlackboardWorkspace


class TestMonitorApi(unittest.TestCase):
    """Test suite for live workflow monitor endpoints."""

    @classmethod
    def setUpClass(cls):
        # Create a test run using WorkflowOrchestrator
        cls.client = TestClient(app)
        sample_xlsx = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "samples",
            "test_input.xlsx",
        )
        if not os.path.exists(sample_xlsx):
            from scripts.generate_mock_excel import generate_benchmark_excel
            generate_benchmark_excel(sample_xlsx)

        cls.orchestrator = WorkflowOrchestrator(offline_mode=True)
        cls.orchestrator.run_pipeline(
            input_files=[sample_xlsx],
            company_name="Test Enterprise Corp",
            facility_name="Test Plant Alpha",
            reporting_year=2026,
        )
        cls.test_run_id = cls.orchestrator.run_id

    def test_monitor_page_served(self):
        """Test GET /monitor serves the HTML page correctly."""
        res = self.client.get("/monitor")
        self.assertEqual(res.status_code, 200)
        self.assertIn("LIVE WORKFLOW MONITOR", res.text)
        self.assertIn("monitor.js", res.text)

    def test_monitor_js_served(self):
        """Test GET /static/monitor.js and GET /monitor.js return javascript content."""
        res1 = self.client.get("/static/monitor.js")
        self.assertEqual(res1.status_code, 200)
        self.assertIn("loadRunsList", res1.text)
        self.assertIn("fetchRunData", res1.text)

        res2 = self.client.get("/monitor.js")
        self.assertEqual(res2.status_code, 200)
        self.assertIn("loadRunsList", res2.text)


    def test_list_runs_endpoint(self):
        """Test GET /api/orchestrator/runs returns structured list of runs."""
        res = self.client.get("/api/orchestrator/runs")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("runs", data)
        self.assertTrue(len(data["runs"]) > 0)

        # Verify first run structure
        first_run = data["runs"][0]
        self.assertIn("run_id", first_run)
        self.assertIn("phase", first_run)
        self.assertIn("progress_pct", first_run)
        self.assertIn("queries_count", first_run)
        self.assertIn("assumptions_count", first_run)
        self.assertIn("deliverables_count", first_run)

    def test_get_run_details(self):
        """Test GET /api/orchestrator/runs/{run_id} returns all intermediate artifacts."""
        res = self.client.get(f"/api/orchestrator/runs/{self.test_run_id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["run_id"], self.test_run_id)
        self.assertIn("state", data)
        self.assertIn("index", data)
        self.assertIn("intermediate", data)
        self.assertIn("scope1", data["intermediate"])
        self.assertIn("scope2", data["intermediate"])
        self.assertIn("scope3", data["intermediate"])
        self.assertIn("mitigation", data["intermediate"])
        self.assertIn("deliverables", data)
        self.assertIn("manifest", data)

    def test_get_run_files_manifest(self):
        """Test GET /api/orchestrator/runs/{run_id}/files returns complete file manifest."""
        res = self.client.get(f"/api/orchestrator/runs/{self.test_run_id}/files")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["run_id"], self.test_run_id)
        self.assertTrue(data["has_state"])
        self.assertTrue(data["has_index"])
        self.assertIn("intermediate", data)
        self.assertIn("deliverables", data)

    def test_get_intermediate_json_file(self):
        """Test GET /api/orchestrator/runs/{run_id}/intermediate/{filename}."""
        res = self.client.get(f"/api/orchestrator/runs/{self.test_run_id}/intermediate/scope1_extracted.json")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsInstance(data, list)
        self.assertTrue(len(data) > 0)

    def test_non_existent_run_404(self):
        """Test 404 for invalid run ID."""
        res = self.client.get("/api/orchestrator/runs/non_existent_run_12345")
        self.assertEqual(res.status_code, 404)


if __name__ == "__main__":
    unittest.main()
