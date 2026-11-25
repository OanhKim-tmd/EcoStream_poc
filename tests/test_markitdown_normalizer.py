"""Tests for MarkItDown normalization (no OCR) and Markdown Table Parser."""

import os
import unittest
from ecostream.ingestion.markitdown_normalizer import MarkItDownNormalizer, NormalizedDocumentContent
from ecostream.ingestion.loaders import DocumentIngestionLoader, IngestedDocument


class TestMarkItDownNormalizer(unittest.TestCase):
    def setUp(self):
        self.normalizer = MarkItDownNormalizer()
        self.samples_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "samples",
        )

    def test_text_fastpath(self):
        fpath = os.path.join(self.samples_dir, "sample_evn_bill.txt")
        res = self.normalizer.normalize_file(fpath)
        self.assertIsInstance(res, NormalizedDocumentContent)
        self.assertEqual(res.converter_used, "NATIVE_TEXT")
        self.assertFalse(res.ocr_applied)
        self.assertIn("45,250", res.markdown_content)

    def test_document_loader_integration(self):
        fpath = os.path.join(self.samples_dir, "sample_fuel_invoice.txt")
        doc = DocumentIngestionLoader.load_file(fpath)
        self.assertIsInstance(doc, IngestedDocument)
        self.assertIn("PETROLIMEX", doc.content.upper())
        self.assertEqual(doc.metadata.get("original_filename"), "sample_fuel_invoice.txt")


if __name__ == "__main__":
    unittest.main()
