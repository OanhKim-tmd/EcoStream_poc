"""Regression tests for encrypted cache, upload validation and safe monitor rendering."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from ecostream.app.server import app, _validate_uploaded_document, HTTPException
from ecostream.ingestion.cache import IngestionCache

ROOT = Path(__file__).resolve().parents[1]


class EncryptedCacheTests(unittest.TestCase):
    def test_cache_files_are_encrypted_and_round_trip_with_deployment_key(self):
        key = Fernet.generate_key().decode("ascii")
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"ECOSTREAM_ENCRYPTION_KEY": key}):
            cache = IngestionCache(directory)
            digest = "a" * 64
            text = "Supplier, Amount\nConfidential Ltd, 12345\n"
            cache_path = cache.store(digest, text)
            raw = Path(cache_path).read_bytes()
            self.assertNotIn(b"Confidential Ltd", raw)
            self.assertTrue(cache_path.endswith(".enc"))
            self.assertEqual(cache.get(digest), text)

    def test_plaintext_legacy_cache_is_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            legacy = Path(directory) / ("b" * 64 + ".md")
            legacy.write_text("sensitive parsed invoice", encoding="utf-8")
            IngestionCache(directory)
            self.assertFalse(legacy.exists())

    def test_cache_rejects_invalid_digest_path(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = IngestionCache(directory)
            with self.assertRaises(ValueError):
                cache.get("../../outside")


class UploadValidationTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_fake_pdf_rejected_by_signature(self):
        response = self.client.post(
            "/api/survey/prepare",
            data={"company": "Test Co", "location": "Plant", "period": "2026"},
            files=[("files", ("invoice.pdf", b"not a pdf", "application/pdf"))],
        )
        self.assertEqual(response.status_code, 422)

    def test_fake_office_archive_rejected(self):
        response = self.client.post(
            "/api/survey/prepare",
            data={"company": "Test Co", "location": "Plant", "period": "2026"},
            files=[("files", ("invoice.xlsx", b"PK\x03\x04not an office archive", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
        )
        self.assertEqual(response.status_code, 422)

    def test_document_validator_rejects_unsupported_extension(self):
        with tempfile.NamedTemporaryFile(suffix=".exe") as temp:
            temp.write(b"MZ\x00\x00")
            temp.flush()
            with self.assertRaises(HTTPException):
                _validate_uploaded_document(temp.name, "program.exe")


class MonitorXssTests(unittest.TestCase):
    def test_dynamic_monitor_values_are_escaped_before_innerhtml(self):
        source = (ROOT / "ecostream/app/static/monitor.js").read_text(encoding="utf-8")
        for field in (
            "sheetLabel", "agentLabel", "t.description", "r.description", "r.category",
            "periodOrMonth", "meterOrDoc", "q.detected_issue", "q.action_taken",
            "a.justification",
        ):
            self.assertIn(f"escapeHtml({field}", source, f"unescaped field: {field}")
        self.assertIn("const escapeHtml =", source)


if __name__ == "__main__":
    unittest.main()
