"""End-to-end integration test for the EcoStream pipeline and API endpoints."""

import unittest
from starlette.testclient import TestClient
from ecostream.app.server import app


class TestPipelineIntegration(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_index_page(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("EcoStream", resp.text)
        self.assertIn("AI DATA ENGINE", resp.text)

    def test_demo_api(self):
        resp = self.client.get("/api/demo")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("summary", data)
        self.assertIn("calculations", data)
        summary = data["summary"]
        self.assertAlmostEqual(summary["total_co2e_tonnes"], 89.379, places=2)
        self.assertAlmostEqual(summary["scope_1_tonnes"], 4.958, places=2)
        self.assertAlmostEqual(summary["scope_2_tonnes"], 32.675, places=2)
        self.assertAlmostEqual(summary["scope_3_tonnes"], 51.746, places=2)
        self.assertEqual(summary["reliability"]["grade"], "A")

    def test_report_export_endpoints(self):
        # HTML Report
        resp_html = self.client.get("/api/report/html")
        self.assertEqual(resp_html.status_code, 200)
        self.assertIn("Báo Cáo Kiểm Kê & Độ Tin Cậy Dữ Liệu Carbon", resp_html.text)

        # Markdown Report
        resp_md = self.client.get("/api/report/markdown")
        self.assertEqual(resp_md.status_code, 200)
        self.assertIn("# BÁO CÁO KIỂM KÊ PHÁT THẢI", resp_md.text)

        # Native Vector PDF Report
        resp_pdf = self.client.get("/api/report/pdf")
        self.assertEqual(resp_pdf.status_code, 200)
        self.assertEqual(resp_pdf.headers["content-type"], "application/pdf")
        self.assertTrue(resp_pdf.content.startswith(b"%PDF"))
        self.assertGreater(len(resp_pdf.content), 1000)

    def test_factors_api(self):
        resp = self.client.get("/api/factors")
        self.assertEqual(resp.status_code, 200)
        factors = resp.json()
        self.assertGreaterEqual(len(factors), 8)
        factor_ids = [f["factor_id"] for f in factors]
        self.assertIn("EF-SCOPE2-VN-GRID", factor_ids)
        self.assertIn("EF-SCOPE1-DIESEL", factor_ids)


if __name__ == "__main__":
    unittest.main()
