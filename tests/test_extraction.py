"""Tests for document loading and parsing from benchmark files."""

import os
import unittest
from ecostream.ingestion.loaders import DocumentIngestionLoader
from ecostream.extraction.extractor import ExtractionEngine
from ecostream.models.activity import EmissionScope


class TestExtraction(unittest.TestCase):
    def setUp(self):
        self.samples_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "samples",
        )
        self.extractor = ExtractionEngine()

    def test_evn_bill_extraction(self):
        fpath = os.path.join(self.samples_dir, "sample_evn_bill.txt")
        doc = DocumentIngestionLoader.load_file(fpath)
        records = self.extractor.extract_document(doc)
        self.assertEqual(len(records), 1)
        r = records[0]
        self.assertEqual(r.scope, EmissionScope.SCOPE_2)
        self.assertEqual(r.unit, "kWh")
        self.assertEqual(r.quantity, 45250.0)
        self.assertTrue("EVN" in r.supplier or "ĐIỆN LỰC" in r.supplier)
        self.assertEqual(r.evidence.document_type, "EVN_BILL")

    def test_fuel_invoice_extraction(self):
        fpath = os.path.join(self.samples_dir, "sample_fuel_invoice.txt")
        doc = DocumentIngestionLoader.load_file(fpath)
        records = self.extractor.extract_document(doc)
        self.assertEqual(len(records), 1)
        r = records[0]
        self.assertEqual(r.scope, EmissionScope.SCOPE_1)
        self.assertEqual(r.unit, "liter")
        self.assertEqual(r.quantity, 1850.0)
        self.assertEqual(r.evidence.document_type, "FUEL_INVOICE")

    def test_freight_log_extraction(self):
        fpath = os.path.join(self.samples_dir, "sample_freight_log.csv")
        doc = DocumentIngestionLoader.load_file(fpath)
        records = self.extractor.extract_document(doc)
        self.assertEqual(len(records), 5)
        for r in records:
            self.assertEqual(r.scope, EmissionScope.SCOPE_3)
            self.assertEqual(r.unit, "ton-km")

    def test_supplier_spend_extraction(self):
        fpath = os.path.join(self.samples_dir, "sample_supplier_spend.csv")
        doc = DocumentIngestionLoader.load_file(fpath)
        records = self.extractor.extract_document(doc)
        self.assertEqual(len(records), 5)
        # 3 physical materials (kg) + 2 spend proxies (VND)
        units = [r.unit for r in records]
        self.assertEqual(units.count("kg"), 3)
        self.assertEqual(units.count("VND"), 2)


if __name__ == "__main__":
    unittest.main()
