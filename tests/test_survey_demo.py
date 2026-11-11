"""End-to-end checks for the explicitly fictional multi-format survey fixture."""
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from openpyxl import load_workbook

from ecostream.app import server
from ecostream.ingestion.survey_workbook import extract_documents
from ecostream.orchestrator.survey_pipeline import (
    INVENTORY_FILE, REPORT_FILE, SURVEY_FILE, calculate_survey, prepare_survey,
)
from scripts.generate_survey_demo import generate


class SurveyDemoTests(unittest.TestCase):
    def test_kwh_in_mixed_ledger_header_does_not_reclassify_fuel(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "mixed.csv"
            source.write_text(
                "Ngày (điện kWh và nhiên liệu),Nhiên liệu,Số lượng,Đơn vị,Mục đích\n"
                "2026-01-12,Dầu Diesel DO,1000,Lít,Máy phát điện\n",
                encoding="utf-8",
            )
            extracted = extract_documents([str(source)], 2026)
            self.assertEqual(len(extracted.items), 1)
            self.assertEqual(extracted.items[0].kind, "diesel")
            self.assertEqual(extracted.items[0].sheet, "1.1")
            self.assertEqual(extracted.items[0].quantity, 1000)

    def test_mixed_ledger_with_electricity_header_retains_fuel_row(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "mixed.csv"
            source.write_text(
                "Kỳ hóa đơn,Sản lượng điện tiêu thụ (kWh),Công tơ demo,Đơn vị,Mục đích\n"
                "2026-01-12,Dầu Diesel DO,1000,Lít,Máy phát điện\n",
                encoding="utf-8",
            )
            extracted = extract_documents([str(source)], 2026)
            self.assertEqual(len(extracted.items), 1)
            self.assertEqual(extracted.items[0].kind, "diesel")

    def test_four_format_upload_via_public_api(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            inputs = generate(folder / "evidence")
            client = TestClient(server.app)
            with patch.object(server, "RUNS_DIR", str(folder / "runs")), ExitStack() as stack:
                files = [
                    ("files", (path.name, stack.enter_context(path.open("rb")), "application/octet-stream"))
                    for path in inputs
                ]
                response = client.post(
                    "/api/survey/prepare",
                    data={"company": "Doanh nghiệp DEMO", "location": "Cơ sở DEMO", "period": "2026"},
                    files=files,
                )
                self.assertEqual(response.status_code, 200, response.text)
                payload = response.json()
                self.assertEqual([f["records"] for f in payload["files"]], [36, 24, 11, 1])
                run_id = payload["run_id"]
                preview = client.get(f"/api/survey/runs/{run_id}/survey/preview")
                self.assertEqual(preview.status_code, 200)
                self.assertIn("30500", preview.text)
                calculated = client.post(f"/api/survey/runs/{run_id}/calculate")
                self.assertEqual(calculated.status_code, 200, calculated.text)
                for name in ("survey", "inventory", "report"):
                    download = client.get(f"/api/survey/runs/{run_id}/files/{name}")
                    self.assertEqual(download.status_code, 200, name)
                    self.assertTrue(download.content)

    def test_four_formats_twelve_months_and_calculation(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            inputs = generate(folder / "evidence")
            self.assertEqual({p.suffix for p in inputs}, {".xlsx", ".docx", ".csv", ".pdf"})
            for path in inputs:
                self.assertTrue(path.exists())
                self.assertGreater(path.stat().st_size, 0)

            extracted = extract_documents([str(p) for p in inputs], 2026)
            electricity = [item for item in extracted.items if item.kind == "electricity"]
            self.assertEqual({item.month for item in electricity}, set(range(1, 13)))
            self.assertEqual(len(electricity), 12)
            self.assertEqual({item.month: item.quantity for item in electricity}[1], 30500)
            self.assertEqual(len([i for i in extracted.items if i.sheet == "1.1"]), 36)
            self.assertEqual(len([i for i in extracted.items if i.sheet == "1.2"]), 24)

            prepared = prepare_survey([str(p) for p in inputs], "Cơ sở demo giả lập", "Nhà máy giả lập", 2026, str(folder / "runs"))
            self.assertEqual(len(prepared["files"]), 4)
            self.assertTrue(all(f["records"] > 0 for f in prepared["files"]), prepared["files"])
            deliverables = folder / "runs" / prepared["run_id"] / "deliverables"
            survey = load_workbook(deliverables / SURVEY_FILE)
            self.assertEqual(survey["2.1"]["E3"].value, 30500)
            self.assertEqual(survey["2.1"]["E9"].value, 33500)  # July is present
            self.assertEqual(survey["1.1"]["F8"].value, 1010)

            result = calculate_survey(prepared["run_id"], base_runs_dir=str(folder / "runs"))
            self.assertEqual(result["stage"], "COMPLETED")
            self.assertGreater(result["summary"]["scope_1_tonnes"], 0)
            self.assertGreater(result["summary"]["scope_2_tonnes"], 0)
            self.assertTrue((deliverables / INVENTORY_FILE).exists())
            self.assertTrue((deliverables / REPORT_FILE).exists())
            inventory = load_workbook(deliverables / INVENTORY_FILE)
            self.assertEqual(inventory["S2-Electricity Consumption"]["C7"].value, 30500)
            self.assertEqual(inventory["S2-Electricity Consumption"]["C13"].value, 33500)


if __name__ == "__main__":
    unittest.main()
