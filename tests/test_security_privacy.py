"""Security test suite for EcoStream: encryption at rest, path traversal, API key auth."""

import os
import shutil
import tempfile
import unittest
from starlette.testclient import TestClient

from ecostream.orchestrator.state import BlackboardWorkspace
from ecostream.app.server import app, _validate_safe_identifier, _verify_safe_path


class TestSecurityAndPrivacy(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.test_dir = tempfile.mkdtemp(prefix="ecostream_sec_test_")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    # ── Mã hóa dữ liệu khi lưu (AES-256 Fernet) ──────────────────────
    def test_encryption_at_rest_for_raw_inputs(self):
        """Verify files in raw_inputs/ are encrypted with AES-256 Fernet."""
        run_id = "test_run_encryption_rest"
        workspace = BlackboardWorkspace(run_id, self.test_dir)

        secret_file = os.path.join(self.test_dir, "invoice_secret.pdf")
        with open(secret_file, "wb") as f:
            f.write(b"%PDF-1.4 SECRET_CUSTOMER_FINANCIAL_INVOICE_DATA")

        dest = workspace.store_raw_input(secret_file)
        self.assertTrue(dest.endswith(".enc"))
        self.assertTrue(os.path.exists(dest))

        # File on disk must be ciphertext, not the plaintext PDF
        with open(dest, "rb") as f:
            disk_content = f.read()
        self.assertFalse(disk_content.startswith(b"%PDF"))
        self.assertNotIn(b"SECRET_CUSTOMER_FINANCIAL_INVOICE_DATA", disk_content)

        decrypted = workspace.read_raw_input("invoice_secret.pdf")
        self.assertEqual(decrypted, b"%PDF-1.4 SECRET_CUSTOMER_FINANCIAL_INVOICE_DATA")

    # ── Chống path traversal ─────────────────────────────────────────
    def test_path_traversal_protection(self):
        """Verify path traversal attempts on file endpoints are rejected."""
        with self.assertRaises(Exception):
            _validate_safe_identifier("../../etc", "run_id")
        with self.assertRaises(Exception):
            _validate_safe_identifier("run/sub", "run_id")
        with self.assertRaises(Exception):
            _validate_safe_identifier("run\\sub", "run_id")
        with self.assertRaises(Exception):
            _verify_safe_path("/home/oanh/eco/runs", "../../../etc/passwd")

        res = self.client.get("/api/orchestrator/runs/..%2F..%2Fetc/intermediate/test.json")
        self.assertIn(res.status_code, [400, 404, 403])

        res2 = self.client.get("/api/orchestrator/runs/valid_run/intermediate/..%2F..%2Fetc%2Fpasswd")
        self.assertIn(res2.status_code, [400, 404, 403])

    # ── Xác thực API key ─────────────────────────────────────────────
    def test_api_key_authentication(self):
        """Verify API key protects endpoints when ECOSTREAM_API_KEY is set."""
        os.environ["ECOSTREAM_API_KEY"] = "eco_prod_secret_token_2026"
        try:
            status_res = self.client.get("/api/auth/status")
            self.assertEqual(status_res.status_code, 200)
            self.assertTrue(status_res.json()["auth_required"])
            self.assertFalse(status_res.json()["authenticated"])

            # No key -> 401
            self.assertEqual(self.client.get("/api/survey/template").status_code, 401)

            # Wrong key -> 401
            res_wrong = self.client.get("/api/survey/template", headers={"X-API-Key": "wrong_token"})
            self.assertEqual(res_wrong.status_code, 401)

            # Valid header -> 200
            res_auth = self.client.get("/api/survey/template", headers={"X-API-Key": "eco_prod_secret_token_2026"})
            self.assertEqual(res_auth.status_code, 200)

            # Query parameter keys are rejected (avoid leaking secrets into URLs/logs).
            res_query = self.client.get("/api/survey/template?api_key=eco_prod_secret_token_2026")
            self.assertEqual(res_query.status_code, 401)
        finally:
            del os.environ["ECOSTREAM_API_KEY"]


if __name__ == "__main__":
    unittest.main()
