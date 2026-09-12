"""Tests for MarkItDown normalization, OCR adapters, and Markdown Table Parser."""

import os
import io
import unittest
from ecostream.ingestion.markitdown_normalizer import MarkItDownNormalizer, NormalizedDocumentContent
from ecostream.ingestion.loaders import DocumentIngestionLoader, IngestedDocument
from ecostream.extraction.parsers import MarkdownTableParser
from ecostream.models.activity import EmissionScope, ActivityCategory
from starlette.testclient import TestClient
from ecostream.app.server import app


class TestMarkItDownNormalizer(unittest.TestCase):
    def setUp(self):
        self.normalizer = MarkItDownNormalizer(enable_ocr=True)
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

    def test_markdown_table_parser_freight_and_materials(self):
        sample_gfm_table = """
# Bảng Kê Xuất Kho và Vận Chuyển

| Tuyến vận chuyển | Tải trọng (tấn) | Quãng đường (km) | Thành tiền (VNĐ) |
| :--- | :---: | :---: | :---: |
| Hà Nội - Hải Phòng (Xuất cảng) | 15.0 | 120.0 | 4,500,000 |
| Bắc Ninh - Hà Nội (Nhập phụ kiện) | 3.5 | 40.0 | 1,200,000 |

| Mặt hàng mua sắm | Số lượng | Đơn vị | Thành tiền (VNĐ) |
| :--- | :---: | :---: | :---: |
| Thùng carton 5 lớp loại A | 2500 | kg | 37,500,000 |
| Phí dịch vụ bốc xếp trung chuyển | | | 15,000,000 |
"""
        doc = IngestedDocument(
            filename="manifest_table.md",
            file_type="EXCEL_SHEET",
            content=sample_gfm_table,
            metadata={"converter": "MARKITDOWN_XLSX", "ocr_applied": False},
        )

        self.assertTrue(MarkdownTableParser.can_parse(doc))
        records = MarkdownTableParser.parse(doc)
        self.assertEqual(len(records), 4)

        # Record 1: Freight
        r1 = records[0]
        self.assertEqual(r1.scope, EmissionScope.SCOPE_3)
        self.assertEqual(r1.category, ActivityCategory.UPSTREAM_TRANSPORTATION)
        self.assertEqual(r1.unit, "ton-km")
        self.assertEqual(r1.quantity, 1800.0)  # 15.0 * 120.0
        self.assertEqual(r1.evidence.page_or_line, "Table Row 1")

        # Record 3: Purchased Materials
        r3 = records[2]
        self.assertEqual(r3.scope, EmissionScope.SCOPE_3)
        self.assertEqual(r3.category, ActivityCategory.PURCHASED_GOODS)
        self.assertEqual(r3.unit, "kg")
        self.assertEqual(r3.quantity, 2500.0)

        # Record 4: Spend proxy fallback
        r4 = records[3]
        self.assertEqual(r4.unit, "VND")
        self.assertEqual(r4.quantity, 15000000.0)
        self.assertTrue(r4.measurement_type.value.startswith("Spend-Based"))

    def test_document_loader_integration(self):
        fpath = os.path.join(self.samples_dir, "sample_fuel_invoice.txt")
        doc = DocumentIngestionLoader.load_file(fpath)
        self.assertIsInstance(doc, IngestedDocument)
        self.assertIn("PETROLIMEX", doc.content.upper())
        self.assertEqual(doc.metadata.get("original_filename"), "sample_fuel_invoice.txt")

    def test_multipart_upload_endpoint(self):
        client = TestClient(app)
        sample_txt = "TỔNG CÔNG TY ĐIỆN LỰC TP HÀ NỘI\nTổng điện năng tiêu thụ: 12,000 kWh\nTổng cộng tiền thanh toán: 24,000,000 đồng"
        
        response = client.post(
            "/api/upload",
            data={
                "company": "Test Textile SME",
                "period": "Tháng 03/2026",
                "location": "Hanoi, Vietnam",
            },
            files=[
                ("files", ("test_evn_bill.txt", sample_txt.encode("utf-8"), "text/plain"))
            ],
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("summary", payload)
        self.assertEqual(payload["summary"]["company_name"], "Test Textile SME")
        self.assertGreater(payload["summary"]["total_co2e_tonnes"], 0)


if __name__ == "__main__":
    unittest.main()
