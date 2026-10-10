"""Unit tests for MarkItDown ingestion and SHA-256 caching layer."""

import os
import unittest
import tempfile
from ecostream.ingestion.cache import IngestionCache
from ecostream.ingestion.markitdown_loader import MarkItDownLoader


class TestMarkItDownIngestion(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache = IngestionCache(cache_dir=os.path.join(self.temp_dir.name, "cache"))
        self.loader = MarkItDownLoader(cache=self.cache)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_csv_ingestion_and_caching(self):
        csv_path = os.path.join(self.temp_dir.name, "test_spend.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("Date,Supplier,Category,Amount_VND\n2026-01-15,Công ty ABC,Vận chuyển,25000000\n")

        # 1st conversion: cache miss
        conv1 = self.loader.convert_file(csv_path)
        self.assertFalse(conv1.is_cache_hit)
        self.assertIn("Công ty ABC", conv1.full_markdown)
        self.assertIn("| Date | Supplier |", conv1.full_markdown)

        # 2nd conversion: cache hit
        conv2 = self.loader.convert_file(csv_path)
        self.assertTrue(conv2.is_cache_hit)
        self.assertEqual(conv1.sha256, conv2.sha256)
        self.assertEqual(conv1.full_markdown, conv2.full_markdown)

    def test_pdf_ingestion_and_caching(self):
        pdf_path = os.path.join(self.temp_dir.name, "test_evn.pdf")
        from scripts.generate_mock_evn_pdf import generate_single_evn_pdf
        generate_single_evn_pdf(
            output_path=pdf_path,
            month=5,
            year=2026,
            company_name="CÔNG TY TNHH TEST PDF ECOSTREAM",
            kwh_bt=25000,
            kwh_cd=9000,
            kwh_td=16000,
        )

        # 1st conversion: cache miss
        conv1 = self.loader.convert_file(pdf_path)
        self.assertFalse(conv1.is_cache_hit)
        self.assertIn("TẬP ĐOÀN ĐIỆN LỰC VIỆT NAM", conv1.full_markdown)
        self.assertIn("TEST PDF ECOSTREAM", conv1.full_markdown)
        self.assertIn("50000 kWh", conv1.full_markdown)  # 25k + 9k + 16k = 50k

        # 2nd conversion: cache hit
        conv2 = self.loader.convert_file(pdf_path)
        self.assertTrue(conv2.is_cache_hit)
        self.assertEqual(conv1.sha256, conv2.sha256)
        self.assertEqual(conv1.full_markdown, conv2.full_markdown)

    def test_excel_sheet_decomposition(self):
        try:
            import openpyxl

            xlsx_path = os.path.join(self.temp_dir.name, "test_multisheet.xlsx")
            wb = openpyxl.Workbook()
            ws1 = wb.active
            ws1.title = "EVN_Electricity"
            ws1.append(["Month", "Active_kWh", "Peak_kWh"])
            ws1.append(["01/2026", 45000, 12000])

            ws2 = wb.create_sheet(title="Fuel_Consumption")
            ws2.append(["Date", "Fuel_Type", "Volume_Liters"])
            ws2.append(["2026-02-10", "DO 0.05S", 1850])

            wb.save(xlsx_path)

            conv = self.loader.convert_file(xlsx_path)
            self.assertIn("EVN_Electricity", conv.sheet_markdowns)
            self.assertIn("Fuel_Consumption", conv.sheet_markdowns)
            self.assertIn("45000", conv.sheet_markdowns["EVN_Electricity"])
            self.assertIn("DO 0.05S", conv.sheet_markdowns["Fuel_Consumption"])
        except ImportError:
            self.skipTest("openpyxl not installed")


if __name__ == "__main__":
    unittest.main()
