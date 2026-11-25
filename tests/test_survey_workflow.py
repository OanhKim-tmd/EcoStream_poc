"""Survey-first workflow contract: template mapping, calculations and guarded API."""
import os
import tempfile
import unittest
from pathlib import Path

from docx import Document
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from ecostream.app import server
from ecostream.app.server import app
from ecostream.ingestion.survey_workbook import (
    SurveyGeneralInfo, SurveyValidationError, read_survey, extract_documents,
)
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

    def test_general_info_written_to_survey_excel_and_parsed_back(self):
        info = SurveyGeneralInfo(
            contact_name="Nguyễn Thu Trang",
            contact_role="Trưởng phòng HSE",
            contact_phone="0912345678",
            contact_email="trang@example.vn",
            facility_name="Nhà máy Dệt May Số 1",
            facility_address="KCN Nam Thăng Long, Bắc Từ Liêm, Hà Nội",
            facility_phone="02438889999",
            facility_email="info@example.vn",
            legal_representative="Trần Đình Minh",
            legal_rep_title="Tổng Giám đốc",
            industry_sector="Sản xuất hàng may mặc",
            operating_status="Đang hoạt động",
            start_year="2018",
            facility_representative="Trần Đình Minh",
        )
        res = prepare_survey(
            [str(SAMPLE)],
            "Công ty CP Dệt May Mẫu",
            "Nhà máy Dệt May Số 1",
            2026,
            self.tmp.name,
            general_info=info,
        )
        survey_path = Path(self.tmp.name) / res["run_id"] / "deliverables" / SURVEY_FILE
        wb = load_workbook(survey_path)
        ws = wb["Thông tin chung"]
        self.assertIn("Nguyễn Thu Trang", ws["B3"].value)
        self.assertIn("Trưởng phòng HSE", ws["B4"].value)
        self.assertIn("0912345678", ws["B5"].value)
        self.assertIn("trang@example.vn", ws["B6"].value)
        self.assertEqual(ws["B8"].value, "1. Tên cơ sở: Nhà máy Dệt May Số 1")
        self.assertIn("KCN Nam Thăng Long", ws["B9"].value)
        self.assertIn("02438889999", ws["B10"].value)
        self.assertIn("info@example.vn", ws["B11"].value)
        self.assertIn("Trần Đình Minh", ws["B12"].value)
        self.assertIn("Tổng Giám đốc", ws["B12"].value)
        self.assertEqual(ws["B14"].value, "- Ngành nghề sản xuất/Loại hình kinh doanh: Sản xuất hàng may mặc")
        self.assertIn("Đang hoạt động", ws["B15"].value)
        self.assertIn("2018", ws["B15"].value)
        self.assertIn("ĐẠI DIỆN CƠ SỞ", ws["B16"].value)
        self.assertEqual(ws["B17"].value, "Trần Đình Minh")

        parsed = read_survey(str(survey_path))
        self.assertIsNotNone(parsed.general_info)
        self.assertEqual(parsed.general_info.contact_name, "Nguyễn Thu Trang")
        self.assertEqual(parsed.general_info.industry_sector, "Sản xuất hàng may mặc")
        self.assertEqual(parsed.general_info.start_year, "2018")
        self.assertEqual(parsed.general_info.legal_rep_title, "Tổng Giám đốc")

        outcome = calculate_survey(res["run_id"], base_runs_dir=self.tmp.name)
        self.assertEqual(outcome["summary"]["industry_sector"], "Sản xuất hàng may mặc")
        docx_text = "\n".join(
            p.text for p in Document(Path(self.tmp.name) / res["run_id"] / "deliverables" / REPORT_FILE).paragraphs
        )
        self.assertIn("KCN Nam Thăng Long", docx_text)
        self.assertIn("Sản xuất hàng may mặc", docx_text)
        self.assertIn("Trần Đình Minh", docx_text)

    def test_empty_optional_fields_preserve_template_placeholders(self):
        wb = load_workbook(self.outputs / SURVEY_FILE)
        ws = wb["Thông tin chung"]
        self.assertEqual(ws["B8"].value, "1. Tên cơ sở: Nhà máy A")
        self.assertIn("Ngành nghề sản xuất/Loại hình kinh doanh", ws["B14"].value)
        self.assertNotIn("Đơn vị cung cấp", ws["B14"].value)
        parsed = read_survey(str(self.outputs / SURVEY_FILE))
        self.assertEqual(parsed.general_info.contact_name, "")
        self.assertEqual(parsed.general_info.industry_sector, "")

    def test_api_prepare_accepts_facility_form_and_updates_preview_and_excel(self):
        from unittest.mock import patch
        client = TestClient(app)
        with patch.object(server, "RUNS_DIR", self.tmp.name):
            with SAMPLE.open("rb") as stream:
                response = client.post(
                    "/api/survey/prepare",
                    data={
                        "company": "Công ty ABC",
                        "location": "Cơ sở Bình Dương",
                        "period": "2026",
                        "contact_name": "Lê Thị Hoa",
                        "contact_role": "Kế toán trưởng",
                        "contact_phone": "0909111222",
                        "contact_email": "hoa@abc.vn",
                        "facility_address": "KCN VSIP II, Bình Dương",
                        "facility_phone": "0274123456",
                        "facility_email": "info@abc.vn",
                        "legal_representative": "Phạm Văn Nam",
                        "legal_rep_title": "Giám đốc",
                        "industry_sector": "Chế biến thực phẩm",
                        "operating_status": "Đang hoạt động",
                        "start_year": "2020",
                        "facility_representative": "=CMD|bad",
                    },
                    files={"files": ("input.xlsx", stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                )
            self.assertEqual(response.status_code, 200, response.text)
            run_id = response.json()["run_id"]
            preview = client.get(f"/api/survey/runs/{run_id}/survey/preview")
            self.assertEqual(preview.status_code, 200)
            self.assertIn("Lê Thị Hoa", preview.text)
            self.assertIn("Chế biến thực phẩm", preview.text)
            wb_resp = client.get(f"/api/survey/runs/{run_id}/survey")
            self.assertEqual(wb_resp.status_code, 200)
            saved_xlsx = Path(self.tmp.name) / "downloaded.xlsx"
            saved_xlsx.write_bytes(wb_resp.content)
            ws = load_workbook(saved_xlsx)["Thông tin chung"]
            self.assertEqual(ws["B8"].value, "1. Tên cơ sở: Cơ sở Bình Dương")
            self.assertIn("KCN VSIP II", ws["B9"].value)
            self.assertTrue(str(ws["B17"].value).startswith("'="))

            # Step 4 download ("Biểu Khảo Sát Đã xác nhận (.xlsx)") after calculate, even if a reviewed workbook cleared/lacked info
            from ecostream.ingestion.survey_workbook import SURVEY_NAME, TEMPLATES
            blank_edited = load_workbook(TEMPLATES / SURVEY_NAME)
            blank_edited["2.1"]["E3"] = 55000
            blank_edited["2.1"]["D3"] = "kWh"
            reviewed_path = Path(self.tmp.name) / "reviewed_blank_info.xlsx"
            blank_edited.save(reviewed_path)
            with reviewed_path.open("rb") as rev_stream:
                calc_resp = client.post(
                    f"/api/survey/runs/{run_id}/calculate",
                    files={"reviewed": ("reviewed_blank_info.xlsx", rev_stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                )
            self.assertEqual(calc_resp.status_code, 200, calc_resp.text)
            confirmed_resp = client.get(f"/api/survey/runs/{run_id}/files/survey")
            self.assertEqual(confirmed_resp.status_code, 200)
            confirmed_xlsx = Path(self.tmp.name) / "confirmed.xlsx"
            confirmed_xlsx.write_bytes(confirmed_resp.content)
            ws_confirmed = load_workbook(confirmed_xlsx)["Thông tin chung"]
            self.assertIn("Lê Thị Hoa", ws_confirmed["B3"].value)
            self.assertEqual(ws_confirmed["B8"].value, "1. Tên cơ sở: Cơ sở Bình Dương")
            self.assertIn("Chế biến thực phẩm", ws_confirmed["B14"].value)
            self.assertEqual(load_workbook(confirmed_xlsx)["2.1"]["E3"].value, 55000)

        index_html = client.get("/").text
        self.assertIn("sectionFacilityInfo", index_html)
        self.assertLess(index_html.index("id=\"sectionFacilityInfo\""), index_html.index("id=\"sectionInput\""))
        self.assertNotIn("btnDemoQuick", index_html)
        self.assertNotIn("runDemoQuick", index_html)
        self.assertNotIn("fillSampleFacilityInfo", index_html)
        for step in (1, 2, 3, 4):
            self.assertIn(f"goToStepIfAllowed({step})", index_html)
        self.assertIn("id=\"btnResetNewRun\"", index_html)
        self.assertLess(index_html.index("id=\"calculationsTableBody\""), index_html.index("id=\"btnResetNewRun\""))
        self.assertIn("text-red-700", index_html)
        for tab_id in ("excelTabBtn-info", "excelTabBtn-11", "excelTabBtn-12", "excelTabBtn-21", "btnSaveSurveyExcel"):
            self.assertIn(tab_id, index_html)

    def test_inline_survey_excel_editor_data_and_save(self):
        from unittest.mock import patch
        client = TestClient(app)
        with patch.object(server, "RUNS_DIR", self.tmp.name):
            with SAMPLE.open("rb") as stream:
                prep = client.post(
                    "/api/survey/prepare",
                    data={"company": "CTY Test", "location": "Xưởng 1", "period": "2026"},
                    files={"files": ("input.xlsx", stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                )
            self.assertEqual(prep.status_code, 200, prep.text)
            run_id = prep.json()["run_id"]

            data_resp = client.get(f"/api/survey/runs/{run_id}/survey/data")
            self.assertEqual(data_resp.status_code, 200, data_resp.text)
            wb_data = data_resp.json()
            self.assertEqual(wb_data["general_info"]["facility_name"], "Xưởng 1")
            self.assertEqual(len(wb_data["sheet_1_1"]), 23)
            self.assertEqual(len(wb_data["sheet_1_2"]), 18)
            self.assertEqual(len(wb_data["sheet_2_1"]), 12)
            for extra_name in ("Phạm vi 1", "1.3", "1.4", "1.5", "1.6", "Phạm vi 2", "2.2", "Thông tin bổ sung", "Biện pháp giảm thiểu", "Cung cap thong tin khai khoang"):
                self.assertIn(extra_name, wb_data["extra_sheets"])

            # Fill missing July (month 7 -> index 6) and edit general info directly
            wb_data["general_info"]["industry_sector"] = "Cơ khí chính xác"
            wb_data["general_info"]["facility_address"] = "KCN Bắc Ninh"
            wb_data["sheet_2_1"][6]["grid_kwh"] = 40000
            # Add LPG (row 13) in month 1 on sheet 1.1 + equipment & supplier columns
            lpg_row = next(r for r in wb_data["sheet_1_1"] if r["kind"] == "lpg")
            lpg_row["months"][0] = 250
            lpg_row["equipment"] = "Bếp tập thể"
            lpg_row["supplier"] = "Petrolimex Gas"
            # Fill row index 1 (row 5 in 1.2) with mobile diesel + vehicle info
            mob_row = wb_data["sheet_1_2"][1]
            mob_row["name"] = "Dầu DO (Diesel)"
            mob_row["material_code"] = "DO-MOB"
            mob_row["unit"] = "liter"
            mob_row["months"][0] = 500
            mob_row["vehicle_type"] = "Xe tải 5T"
            mob_row["distance_km"] = "12000"

            save_resp = client.post(
                f"/api/survey/runs/{run_id}/survey/save",
                json={
                    "general_info": wb_data["general_info"],
                    "sheet_1_1": wb_data["sheet_1_1"],
                    "sheet_1_2": wb_data["sheet_1_2"],
                    "sheet_2_1": wb_data["sheet_2_1"],
                    "extra_cells": {
                        "1.4": {"F4": "12"},
                        "2.2": {"C4": "150"},
                        "Biện pháp giảm thiểu": {"D4": "Thay đèn LED"},
                    },
                },
            )
            self.assertEqual(save_resp.status_code, 200, save_resp.text)
            saved_json = save_resp.json()
            self.assertEqual(saved_json["general_info"]["industry_sector"], "Cơ khí chính xác")
            self.assertEqual(saved_json["sheet_2_1"][6]["grid_kwh"], 40000.0)

            # Verify the actual .xlsx file was updated in place
            dl = client.get(f"/api/survey/runs/{run_id}/files/survey")
            self.assertEqual(dl.status_code, 200)
            out_xlsx = Path(self.tmp.name) / "inline_saved.xlsx"
            out_xlsx.write_bytes(dl.content)
            book = load_workbook(out_xlsx)
            self.assertIn("Cơ khí chính xác", book["Thông tin chung"]["B14"].value)
            self.assertIn("KCN Bắc Ninh", book["Thông tin chung"]["B9"].value)
            self.assertEqual(book["2.1"]["E9"].value, 40000)
            self.assertEqual(book["1.1"]["F13"].value, 250)
            self.assertEqual(book["1.1"]["T13"].value, "Bếp tập thể")
            self.assertEqual(book["1.1"]["U13"].value, "Petrolimex Gas")
            self.assertEqual(book["1.2"]["F5"].value, 500)
            self.assertEqual(book["1.2"]["T5"].value, "Xe tải 5T")
            self.assertEqual(book["1.2"]["V5"].value, 12000)
            self.assertEqual(book["1.4"]["F4"].value, 12)
            self.assertEqual(book["2.2"]["C4"].value, 150)
            self.assertEqual(book["Biện pháp giảm thiểu"]["D4"].value, "Thay đèn LED")

            # Verify proportional Excel column widths (wide text cols > narrow STT/month cols)
            self.assertGreaterEqual(book["1.1"].column_dimensions["C"].width, 36.0)
            self.assertLessEqual(book["1.1"].column_dimensions["B"].width, 7.0)
            self.assertGreaterEqual(book["1.2"].column_dimensions["C"].width, 24.0)
            self.assertGreaterEqual(book["1.1"].column_dimensions["F"].width, 10.5)

            # Verify responsive col_tier metadata for extra sheets
            mit_rows = wb_data["extra_sheets"]["Biện pháp giảm thiểu"]["rows"]
            hdr_tiers = {c["value"]: c["col_tier"] for c in mit_rows[1]}
            self.assertEqual(hdr_tiers["TT"], "narrow")
            self.assertEqual(hdr_tiers["Mô tả sơ bộ giải pháp"], "wide")

            # Calculate straight from the edited .xlsx
            calc_resp = client.post(f"/api/survey/runs/{run_id}/calculate")
            self.assertEqual(calc_resp.status_code, 200, calc_resp.text)
            self.assertEqual(calc_resp.json()["summary"]["industry_sector"], "Cơ khí chính xác")

            # Custom unmapped fuel name in 1.2 and 1.1 row 26 can be saved directly into Excel
            custom_mob = saved_json["sheet_1_2"][2]
            custom_mob["name"] = "Nhiên liệu Hydro (H2)"
            custom_mob["unit"] = "kg"
            custom_mob["months"][0] = 300
            custom_11 = saved_json["sheet_1_1"][-1]
            custom_11["name"] = "Vỏ hạt điều"
            custom_11["unit"] = "kg"
            custom_11["months"][0] = 500
            custom_save = client.post(
                f"/api/survey/runs/{run_id}/survey/save",
                json={
                    "sheet_1_1": saved_json["sheet_1_1"],
                    "sheet_1_2": saved_json["sheet_1_2"],
                },
            )
            self.assertEqual(custom_save.status_code, 200, custom_save.text)
            self.assertTrue(len(custom_save.json().get("save_warnings", [])) >= 2)
            dl2 = client.get(f"/api/survey/runs/{run_id}/files/survey")
            custom_xlsx = Path(self.tmp.name) / "custom_fuel.xlsx"
            custom_xlsx.write_bytes(dl2.content)
            book2 = load_workbook(custom_xlsx)
            self.assertEqual(book2["1.2"]["C6"].value, "Nhiên liệu Hydro (H2)")
            self.assertEqual(book2["1.2"]["F6"].value, 300)
            self.assertEqual(book2["1.1"]["C26"].value, "Vỏ hạt điều")
            self.assertEqual(book2["1.1"]["F26"].value, 500)

    def test_upload_more_than_20_files_up_to_100(self):
        from unittest.mock import patch
        client = TestClient(app)
        with patch.object(server, "RUNS_DIR", self.tmp.name):
            csv_bytes = (
                "Ngày,Nhiên liệu,Số lượng,Đơn vị,Mục đích\n"
                "2026-01-10,Dầu Diesel DO,10,Lít,Máy phát\n"
            ).encode("utf-8")
            files = [
                ("files", (f"fuel_{i:02d}.csv", csv_bytes, "text/csv"))
                for i in range(1, 26)
            ]
            resp = client.post(
                "/api/survey/prepare",
                data={"company": "CTY 25 File", "location": "Kho 1", "period": "2026"},
                files=files,
            )
            self.assertEqual(resp.status_code, 200, resp.text)
            self.assertEqual(len(resp.json()["files"]), 25)
            self.assertIn("Tối đa 100 tệp", client.get("/").text)

    def test_fuel_vat_invoice_pdf_extraction_12_months(self):
        from scripts.generate_mock_fuel_pdf import generate_annual_fuel_pdf
        pdf_path = Path(self.tmp.name) / "fuel_12_months.pdf"
        generate_annual_fuel_pdf(pdf_path, year=2026)
        extracted = extract_documents([str(pdf_path)], 2026)
        self.assertEqual(len(extracted.items), 24)
        self.assertEqual(extracted.warnings, [])
        petrol_items = [i for i in extracted.items if i.kind == "petrol"]
        diesel_items = [i for i in extracted.items if i.kind == "diesel"]
        self.assertEqual(len(petrol_items), 12)
        self.assertEqual(len(diesel_items), 12)
        self.assertTrue(all(i.sheet == "1.2" for i in petrol_items))
        self.assertTrue(all(i.sheet == "1.1" for i in diesel_items))
        self.assertEqual({i.month for i in petrol_items}, set(range(1, 13)))
        self.assertEqual(next(i.quantity for i in petrol_items if i.month == 1), 312.5)
        self.assertEqual(next(i.quantity for i in diesel_items if i.month == 1), 1240.0)

    def test_png_fuel_invoice_upload_and_ocr_extraction(self):
        from unittest.mock import patch
        png_file = ROOT / "data/hóa đơn xăng dầu.png"
        if not png_file.exists():
            self.skipTest("Sample PNG invoice not present")
        client = TestClient(app)
        self.assertIn(".png", client.get("/").text)
        with patch.object(server, "RUNS_DIR", self.tmp.name):
            with png_file.open("rb") as stream:
                resp = client.post(
                    "/api/survey/prepare",
                    data={"company": "CTY PNG Test", "location": "Cơ sở PNG", "period": "2025"},
                    files={"files": ("hóa đơn xăng dầu.png", stream, "image/png")},
                )
            self.assertEqual(resp.status_code, 200, resp.text)
            payload = resp.json()
            self.assertEqual(len(payload["items"]), 1)
            self.assertEqual(payload["items"][0]["kind"], "petrol")
            self.assertEqual(payload["items"][0]["month"], 1)
            self.assertAlmostEqual(payload["items"][0]["quantity"], 46.38, places=2)
            run_id = payload["run_id"]
            wb = load_workbook(Path(self.tmp.name) / run_id / "deliverables" / SURVEY_FILE)
            self.assertAlmostEqual(wb["1.1"]["F11"].value, 46.38, places=2)

    def test_extra_cells_thong_tin_chung_does_not_crash_prepare(self):
        from unittest.mock import patch
        full_xlsx = ROOT / "data/samples/du_lieu_gia_lap_full_2026.xlsx"
        pdf_06 = ROOT / "data/samples/pdf_invoices_2026/06_Ho_so_co_so_va_giam_nhe_KNK_2026.pdf"
        if not full_xlsx.exists() or not pdf_06.exists():
            self.skipTest("Full mock dataset not present")
        client = TestClient(app)
        with patch.object(server, "RUNS_DIR", self.tmp.name):
            with full_xlsx.open("rb") as f1, pdf_06.open("rb") as f2:
                resp = client.post(
                    "/api/survey/prepare",
                    data={
                        "company": "Công ty Test Merge",
                        "location": "Nhà máy Merge",
                        "period": "2026",
                        "industry_sector": "Dệt may thử nghiệm",
                    },
                    files=[
                        ("files", ("du_lieu_gia_lap_full_2026.xlsx", f1, "application/octet-stream")),
                        ("files", ("06_Ho_so_co_so_va_giam_nhe_KNK_2026.pdf", f2, "application/pdf")),
                    ],
                )
            self.assertEqual(resp.status_code, 200, resp.text)
            run_id = resp.json()["run_id"]
            wb = load_workbook(Path(self.tmp.name) / run_id / "deliverables" / SURVEY_FILE)
            self.assertEqual(wb["Thông tin chung"]["B8"].value, "1. Tên cơ sở: Nhà máy Merge")
            self.assertIn("Dệt may thử nghiệm", wb["Thông tin chung"]["B14"].value)


if __name__ == "__main__":
    unittest.main()
