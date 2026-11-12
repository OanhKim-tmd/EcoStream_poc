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
        self.assertTrue("AI ORCHESTRATOR" in resp.text or "AI DATA ENGINE" in resp.text)

    def test_demo_api(self):
        resp = self.client.get("/api/demo")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("summary", data)
        self.assertIn("calculations", data)
        summary = data["summary"]
        self.assertAlmostEqual(summary["total_co2e_tonnes"], 4933.80, places=1)
        self.assertAlmostEqual(summary["scope_1_tonnes"], 4914.82, places=1)
        self.assertAlmostEqual(summary["scope_2_tonnes"], 18.98, places=1)
        self.assertAlmostEqual(summary["scope_3_tonnes"], 0.0, places=1)
        self.assertIn(summary["reliability"]["grade"], ["A", "B", "C"])

    def test_report_export_endpoints(self):
        # HTML Report
        resp_html = self.client.get("/api/report/html")
        self.assertEqual(resp_html.status_code, 200)
        self.assertIn("Báo Cáo Kiểm Kê", resp_html.text)

        # Markdown Report
        resp_md = self.client.get("/api/report/markdown")
        self.assertEqual(resp_md.status_code, 200)
        self.assertIn("BÁO CÁO", resp_md.text)

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

    def test_multi_tenant_auth_and_license_tier_gating(self):
        # 1. Free login
        res_free = self.client.post(
            "/api/auth/login",
            json={"email": "ketoan@congty-a.vn", "org_id": "congty-a", "license_key": None},
        )
        self.assertEqual(res_free.status_code, 200)
        data_free = res_free.json()
        self.assertEqual(data_free["tier"], "FREE")
        self.assertFalse(data_free["is_pro"])
        self.assertEqual(data_free["org_id"], "congty-a")

        # 2. Pro login with valid license key
        res_pro = self.client.post(
            "/api/auth/login",
            json={"email": "hse@congty-a.vn", "org_id": "congty-a", "license_key": "ECO-PRO-2026"},
        )
        self.assertEqual(res_pro.status_code, 200)
        data_pro = res_pro.json()
        self.assertEqual(data_pro["tier"], "PRO")
        self.assertTrue(data_pro["is_pro"])

        # 3. Run demo with org_id and verify per-run report & watermark behavior
        demo_res = self.client.get("/api/demo?org_id=congty-a&user_id=user123")
        self.assertEqual(demo_res.status_code, 200)
        run_id = demo_res.json().get("run_id")
        self.assertTrue(run_id)

        # Free tier HTML preview has watermark
        html_free = self.client.get(f"/api/report/html?run_id={run_id}&tier=free")
        self.assertEqual(html_free.status_code, 200)
        self.assertIn("FREE PREVIEW", html_free.text)

        # Pro tier HTML has no watermark
        html_pro = self.client.get(f"/api/report/html?run_id={run_id}&tier=free&license_key=ECO-PRO-2026")
        self.assertEqual(html_pro.status_code, 200)
        self.assertNotIn("FREE PREVIEW", html_pro.text)

        # Free tier DOCX & Excel are gated with 402 Payment Required
        docx_free = self.client.get(f"/api/report/docx?run_id={run_id}&tier=free")
        self.assertEqual(docx_free.status_code, 402)
        excel_free = self.client.get(f"/api/report/excel?run_id={run_id}&tier=free")
        self.assertEqual(excel_free.status_code, 402)

        # Pro license unlocks DOCX & Excel for that specific run_id
        docx_pro = self.client.get(f"/api/report/docx?run_id={run_id}&tier=free&license_key=ECO-PRO-2026")
        self.assertEqual(docx_pro.status_code, 200)
        excel_pro = self.client.get(f"/api/report/excel?run_id={run_id}&tier=free&license_key=ECO-PRO-2026")
        self.assertEqual(excel_pro.status_code, 200)


if __name__ == "__main__":
    unittest.main()
