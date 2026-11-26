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
        self.assertIn("Kiểm kê Khí nhà kính", resp.text)

    def test_factors_api(self):
        resp = self.client.get("/api/factors")
        self.assertEqual(resp.status_code, 200)
        factors = resp.json()
        self.assertGreaterEqual(len(factors), 8)
        factor_ids = [f["factor_id"] for f in factors]
        self.assertIn("EF-SCOPE2-VN-GRID", factor_ids)
        self.assertIn("EF-SCOPE1-DIESEL", factor_ids)

    def test_ui_has_no_paywall_or_external_cdn(self):
        """No license, tier or watermark markers; no external CDN in the shipped page."""
        for path in ("/api/auth/login", "/api/license/verify", "/api/settings/ai"):
            self.assertIn(self.client.post(path, json={}).status_code, (404, 405))
        page = self.client.get("/").text
        for marker in ("ECO-PRO-2026", "handleProDownload", "Mở khóa", "cdn.tailwindcss.com", "fonts.googleapis.com"):
            self.assertNotIn(marker, page)


if __name__ == "__main__":
    unittest.main()
