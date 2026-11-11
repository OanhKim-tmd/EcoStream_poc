"""Survey-first workflow contract: template mapping, calculations and guarded API."""
import os
import tempfile
import unittest
from pathlib import Path

from docx import Document
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from ecostream.app.server import app
from ecostream.ingestion.survey_workbook import SurveyValidationError, read_survey, extract_documents
from ecostream.orchestrator.survey_pipeline import prepare_survey, calculate_survey, INVENTORY_FILE, REPORT_FILE, SURVEY_FILE

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data/samples/input.xlsx"


class SurveyWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.result = prepare_survey([str(SAMPLE)], "Cơ sở kiểm thử", "Nhà máy A", 2026, self.tmp.name)
        self.run_id = self.result["run_id"]
        self.outputs = Path(self.tmp.name) / self.run_id / "deliverables"

    def test_evn_invoice_pdf_uses_only_active_energy_total(self):
        invoice = ROOT / "data/samples/sample_evn_bill.pdf"
        annual = ROOT / "data/samples/sample_evn_annual_2026.pdf"
        extracted = extract_documents([str(invoice), str(annual)], 2026)
        self.assertEqual(len(extracted.items), 11)
        self.assertEqual({item.month for item in extracted.items}, {1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12})
        self.assertEqual([item.quantity for item in extracted.items if item.month == 3], [45250])
        self.assertTrue(any("bỏ dòng trùng" in warning for warning in extracted.warnings))

    def test_prepared_survey_and_manifest(self):
        self.assertEqual(self.result["stage"], "REVIEW_SURVEY")
        self.assertEqual(self.result["files"][0]["records"], 15)
        survey = read_survey(str(self.outputs / SURVEY_FILE))
        self.assertEqual(len(survey.items), 15)
        book = load_workbook(self.outputs / SURVEY_FILE)
        self.assertEqual(book["1.1"]["H8"].value, 12500)
        self.assertEqual(book["1.1"]["N7"].value, 450000)
        self.assertEqual(book["1.2"]["K4"].value, 3400)
        self.assertEqual(book["2.1"]["E3"].value, 45250)
        self.assertIsNone(book["2.1"]["E9"].value)  # missing July: never interpolate

    def test_calculation_uses_survey_and_removes_sample_activity(self):
        outcome = calculate_survey(self.run_id, base_runs_dir=self.tmp.name)
        self.assertEqual(outcome["stage"], "COMPLETED")
        self.assertAlmostEqual(outcome["summary"]["total_co2e_tonnes"], 1556.556, places=3)
        wb = load_workbook(self.outputs / INVENTORY_FILE)
        self.assertEqual(wb["S1-Stationary Combustion"]["F18"].value, 12500)
        self.assertEqual(wb["S2-Electricity Consumption"]["C7"].value, 45250)
        self.assertIsNone(wb["S2-Electricity Consumption"]["E13"].value)
        self.assertIsNone(wb["S2-Electricity Consumption"]["C13"].value)
        self.assertEqual(wb["S2-Electricity Consumption"]["F19"].value, "=SUM(F7:F18)")
        self.assertAlmostEqual(wb["EcoStream đối soát"]["B14"].value, 1556.556, places=3)
        text = "\n".join(p.text for p in Document(self.outputs / REPORT_FILE).paragraphs)
        self.assertIn("Cơ sở kiểm thử", text)
        self.assertIn("Chưa đủ PTCS", text)
        self.assertNotIn("EcoGarment Vietnam", text)

    def test_reviewed_survey_changes_calculation(self):
        reviewed = Path(self.tmp.name) / "edited.xlsx"
        book = load_workbook(self.outputs / SURVEY_FILE)
        book["2.1"]["E3"] = 90000
        book.save(reviewed)
        outcome = calculate_survey(self.run_id, str(reviewed), self.tmp.name)
        self.assertEqual(outcome["stage"], "COMPLETED")
        self.assertEqual(load_workbook(self.outputs / INVENTORY_FILE)["S2-Electricity Consumption"]["C7"].value, 90000)
        self.assertEqual(load_workbook(self.outputs / SURVEY_FILE)["2.1"]["E3"].value, 90000)

    def test_invalid_review_does_not_replace_original(self):
        reviewed = Path(self.tmp.name) / "bad.xlsx"
        book = load_workbook(self.outputs / SURVEY_FILE)
        book["2.1"]["E3"] = -10
        book.save(reviewed)
        with self.assertRaises(SurveyValidationError):
            calculate_survey(self.run_id, str(reviewed), self.tmp.name)
        self.assertEqual(load_workbook(self.outputs / SURVEY_FILE)["2.1"]["E3"].value, 45250)
        self.assertFalse((self.outputs / INVENTORY_FILE).exists())

    def test_unsupported_fuel_is_rejected_without_outputs(self):
        reviewed = Path(self.tmp.name) / "unsupported.xlsx"
        book = load_workbook(self.outputs / SURVEY_FILE)
        book["1.1"]["C8"] = "Nhiên liệu không xác định"
        book.save(reviewed)
        with self.assertRaisesRegex(SurveyValidationError, "1.1!C8"):
            calculate_survey(self.run_id, str(reviewed), self.tmp.name)
        self.assertFalse((self.outputs / INVENTORY_FILE).exists())

    def test_api_preview_and_download(self):
        client = TestClient(app)
        # Server uses its configured runs folder; prepare through the same public API.
        with SAMPLE.open("rb") as stream:
            response = client.post("/api/survey/prepare", data={"company": "Test", "location": "Facility", "period": "2026"}, files={"files": ("input.xlsx", stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        self.assertEqual(response.status_code, 200, response.text)
        run_id = response.json()["run_id"]
        preview = client.get(f"/api/survey/runs/{run_id}/survey/preview")
        self.assertEqual(preview.status_code, 200)
        self.assertIn("12500", preview.text)
        self.assertEqual(client.get(f"/api/survey/runs/{run_id}/survey").status_code, 200)
        calculated = client.post(f"/api/survey/runs/{run_id}/calculate")
        self.assertEqual(calculated.status_code, 200, calculated.text)
        self.assertEqual(client.get(f"/api/survey/runs/{run_id}/files/report").status_code, 200)


if __name__ == "__main__":
    unittest.main()
