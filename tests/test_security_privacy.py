"""Comprehensive security, confidentiality, and privacy test suite for EcoStream."""

import os
import shutil
import tempfile
import unittest
from starlette.testclient import TestClient

from ecostream.privacy.pii_masker import PIIMasker, MaskMapping, DataSanitizer
from ecostream.privacy.encryption import StorageEncryption
from ecostream.orchestrator.pipeline import WorkflowOrchestrator
from ecostream.orchestrator.state import BlackboardWorkspace
from ecostream.app.server import app, _validate_safe_identifier, _verify_safe_path
from scripts.generate_mock_excel import generate_benchmark_excel


class TestSecurityAndPrivacy(unittest.TestCase):
    """Verifies all 5 enterprise security & privacy pillars."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.test_dir = tempfile.mkdtemp(prefix="ecostream_sec_test_")
        cls.mock_excel = os.path.join(cls.test_dir, "test_input.xlsx")
        generate_benchmark_excel(cls.mock_excel)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    # ── Pillar 1: Data Sanitization (Loại bỏ bí mật thương mại) ──────
    def test_data_sanitizer_strips_commercial_columns(self):
        """Verify unit price, total amount, and discount columns are excised from tables."""
        raw_table = (
            "| Kỳ | Loại nhiên liệu | Số lượng | Đơn vị | Đơn giá (VNĐ) | Thành tiền (VNĐ) | Chiết khấu |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
            "| Tháng 01/2026 | Dầu Diesel (DO) | 1,850 | Lít | 22,500 | 41,625,000 | 0% |\n"
            "| Tháng 02/2026 | Xăng RON 95 | 450 | Lít | 23,800 | 10,710,000 | 2% |\n"
        )
        sanitized = DataSanitizer.sanitize_text(raw_table)

        # Commercial secrets must be removed
        self.assertNotIn("Đơn giá", sanitized)
        self.assertNotIn("Thành tiền", sanitized)
        self.assertNotIn("Chiết khấu", sanitized)
        self.assertNotIn("41,625,000", sanitized)
        self.assertNotIn("10,710,000", sanitized)

        # Physical emission metrics must be preserved
        self.assertIn("Tháng 01/2026", sanitized)
        self.assertIn("Dầu Diesel (DO)", sanitized)
        self.assertIn("1,850", sanitized)
        self.assertIn("Lít", sanitized)
        self.assertIn("Tháng 02/2026", sanitized)
        self.assertIn("450", sanitized)

    def test_data_sanitizer_strips_commercial_lines(self):
        """Verify commercial financial lines and bank details are excised from unstructured text."""
        raw_text = (
            "HÓA ĐƠN TIÊU THỤ ĐIỆN NĂNG THÁNG 01/2026\n"
            "Số công tơ: EVN-HN-884920\n"
            "Sản lượng điện tiêu thụ: 45,250 kWh\n"
            "Đơn giá: 1,890 VNĐ/kWh\n"
            "Thành tiền: 85,522,500 VNĐ\n"
            "Tiền thuế GTGT: 8,552,250 VNĐ\n"
            "Tổng cộng tiền thanh toán: 94,074,750 VNĐ\n"
            "Số tài khoản: 0011004567890 mở tại Ngân hàng Vietcombank\n"
            "Tổng số tiền viết bằng chữ: Chín mươi tư triệu không trăm bảy mươi tư nghìn đồng\n"
        )
        sanitized = DataSanitizer.sanitize_text(raw_text)

        self.assertNotIn("Đơn giá:", sanitized)
        self.assertNotIn("Thành tiền:", sanitized)
        self.assertNotIn("85,522,500", sanitized)
        self.assertNotIn("Tổng cộng tiền thanh toán", sanitized)
        self.assertNotIn("Số tài khoản:", sanitized)
        self.assertNotIn("Tổng số tiền viết bằng chữ", sanitized)

        # Essential activity metrics remain
        self.assertIn("45,250 kWh", sanitized)
        self.assertIn("EVN-HN-884920", sanitized)

    def test_pii_masker_covers_email_phone_cccd_fdi(self):
        """Verify masker replaces personal identity, phones, emails, CCCD, and FDI companies."""
        masker = PIIMasker()
        mapping = MaskMapping()

        text = (
            "Người lập biểu: Nguyễn Văn Bình\n"
            "Số CCCD: 001092004567\n"
            "Email: contact@ecogarment.com.vn\n"
            "Điện thoại: 0987654321\n"
            "Đối tác FDI: Foxconn Precision Industry Co., Ltd\n"
            "Số tài khoản: 19028394827162 tại Techcombank\n"
        )
        masked, mapping = masker.mask_text(text, mapping)

        self.assertNotIn("Nguyễn Văn Bình", masked)
        self.assertNotIn("001092004567", masked)
        self.assertNotIn("contact@ecogarment.com.vn", masked)
        self.assertNotIn("0987654321", masked)
        self.assertNotIn("Foxconn Precision Industry Co., Ltd", masked)
        self.assertNotIn("19028394827162", masked)

        self.assertIn("[PERSON_001]", masked)
        self.assertIn("[CITIZEN_ID_001]", masked)
        self.assertIn("[EMAIL_001]", masked)
        self.assertIn("[PHONE_001]", masked)
        self.assertIn("[COMPANY_001]", masked)
        self.assertIn("[BANK_001]", masked)

        # Unmasking restores the original text exactly
        unmasked = mapping.unmask_text(masked)
        self.assertIn("Nguyễn Văn Bình", unmasked)
        self.assertIn("001092004567", unmasked)
        self.assertIn("Foxconn Precision Industry Co., Ltd", unmasked)

    # ── Pillar 2: In-Memory Mapping (Không ghi ra ổ cứng) ────────────
    def test_in_memory_mapping_never_persisted_to_disk(self):
        """Verify pii_mapping.json is never saved on disk during or after pipeline execution."""
        run_id = "test_run_sec_in_memory"
        orch = WorkflowOrchestrator(run_id=run_id, base_runs_dir=self.test_dir, offline_mode=True)
        orch.run_pipeline(
            input_files=[self.mock_excel],
            company_name="Confidential Textiles JSC",
            facility_name="Confidential Factory Nam Dinh",
            reporting_year=2026,
        )

        pii_file_on_disk = os.path.join(orch.workspace.run_dir, "pii_mapping.json")
        self.assertFalse(
            os.path.exists(pii_file_on_disk),
            "CRITICAL SECURITY DEFECT: pii_mapping.json was saved to disk!",
        )

        # Check in intermediate folder as well
        intermediate_pii = os.path.join(orch.workspace.intermediate_dir, "pii_mapping.json")
        self.assertFalse(os.path.exists(intermediate_pii))

    def test_mask_mapping_memory_clearing(self):
        """Verify MaskMapping.clear() zeroes out RAM dictionaries."""
        mapping = MaskMapping()
        token = mapping.mask("Secret Corp", "COMPANY")
        self.assertEqual(token, "[COMPANY_001]")
        self.assertIn("Secret Corp", mapping._forward)

        mapping.clear()
        self.assertEqual(len(mapping._forward), 0)
        self.assertEqual(len(mapping._reverse), 0)
        self.assertEqual(len(mapping._counters), 0)

    # ── Pillar 3: Encryption at Rest (Mã hóa raw_inputs/ bằng AES-256) ─
    def test_encryption_at_rest_for_raw_inputs(self):
        """Verify files in raw_inputs/ are encrypted with AES-256 Fernet."""
        run_id = "test_run_encryption_rest"
        workspace = BlackboardWorkspace(run_id, self.test_dir)

        # Create sample secret invoice
        secret_file = os.path.join(self.test_dir, "invoice_secret.pdf")
        with open(secret_file, "wb") as f:
            f.write(b"%PDF-1.4 SECRET_CUSTOMER_FINANCIAL_INVOICE_DATA")

        dest = workspace.store_raw_input(secret_file)
        self.assertTrue(dest.endswith(".enc"))
        self.assertTrue(os.path.exists(dest))

        # Check file content on disk is ciphertext, not plaintext PDF
        with open(dest, "rb") as f:
            disk_content = f.read()
        self.assertFalse(disk_content.startswith(b"%PDF"))
        self.assertNotIn(b"SECRET_CUSTOMER_FINANCIAL_INVOICE_DATA", disk_content)

        # Decrypt in memory directly
        decrypted = workspace.read_raw_input("invoice_secret.pdf")
        self.assertEqual(decrypted, b"%PDF-1.4 SECRET_CUSTOMER_FINANCIAL_INVOICE_DATA")

    # ── Pillar 4: Web API Hardening ──────────────────────────────────
    def test_path_traversal_protection(self):
        """Verify Path Traversal attempts on file endpoints are rejected."""
        # 1. Directory traversal in run_id
        with self.assertRaises(Exception):
            _validate_safe_identifier("../../etc", "run_id")

        with self.assertRaises(Exception):
            _validate_safe_identifier("run/sub", "run_id")

        with self.assertRaises(Exception):
            _validate_safe_identifier("run\\sub", "run_id")

        # 2. File traversal in filename
        with self.assertRaises(Exception):
            _verify_safe_path("/home/oanh/eco/runs", "../../../etc/passwd")

        # 3. HTTP endpoint rejects path traversal
        res = self.client.get("/api/orchestrator/runs/..%2F..%2Fetc/intermediate/test.json")
        self.assertIn(res.status_code, [400, 404, 403])

        res2 = self.client.get("/api/orchestrator/runs/valid_run/intermediate/..%2F..%2Fetc%2Fpasswd")
        self.assertIn(res2.status_code, [400, 404, 403])

    def test_api_key_authentication(self):
        """Verify API Key authorization protects endpoints when ECOSTREAM_API_KEY is active."""
        os.environ["ECOSTREAM_API_KEY"] = "eco_prod_secret_token_2026"
        try:
            # Check auth status endpoint
            status_res = self.client.get("/api/auth/status")
            self.assertEqual(status_res.status_code, 200)
            self.assertTrue(status_res.json()["auth_required"])
            self.assertFalse(status_res.json()["authenticated"])

            # Request without key -> 401 Unauthorized
            res_unauth = self.client.get("/api/demo")
            self.assertEqual(res_unauth.status_code, 401)

            # Request with incorrect key -> 401 Unauthorized
            res_wrong = self.client.get("/api/demo", headers={"X-API-Key": "wrong_token"})
            self.assertEqual(res_wrong.status_code, 401)

            # Request with valid key -> 200 OK
            res_auth = self.client.get("/api/demo", headers={"X-API-Key": "eco_prod_secret_token_2026"})
            self.assertEqual(res_auth.status_code, 200)

            # Request with valid query parameter -> 200 OK
            res_query = self.client.get("/api/demo?api_key=eco_prod_secret_token_2026")
            self.assertEqual(res_query.status_code, 200)

        finally:
            del os.environ["ECOSTREAM_API_KEY"]

    # ── Pillar 5: Local-First / Offline Engine ────────────────────────
    def test_local_first_offline_mode_default(self):
        """Verify pipeline runs 100% offline without requiring internet access."""
        orch = WorkflowOrchestrator(base_runs_dir=self.test_dir)
        self.assertTrue(orch.offline_mode)

        res = orch.run_pipeline(
            input_files=[self.mock_excel],
            company_name="Offline Green Energy JSC",
            facility_name="Nha May Ha Nam",
            reporting_year=2026,
        )
        self.assertEqual(res["status"], "COMPLETED")
        self.assertGreater(res["summary"]["total_co2e_tonnes"], 0)


if __name__ == "__main__":
    unittest.main()
