"""Three-stage document → reviewable survey → inventory → report workflow."""
from __future__ import annotations

import json
import secrets
import tempfile
import os
from datetime import datetime, timezone
from pathlib import Path

from ecostream.engine.advisor import CarbonAdvisor
from ecostream.engine.calculator import CarbonCalculator
from ecostream.engine.reliability import ReliabilityEngine
from ecostream.factors.database import get_factor_database
from ecostream.ingestion.survey_workbook import (
    FUEL_NAMES, SurveyData, SurveyItem, SurveyValidationError, extract_documents, read_survey,
)
from ecostream.models.activity import (
    ActivityCategory, ActivityRecord, DataQualityIndicator, EmissionScope,
    EvidenceProvenance, MeasurementType,
)
from ecostream.models.results import AuditReport
from ecostream.models.state import PipelinePhase
from ecostream.orchestrator.state import BlackboardWorkspace
from ecostream.reporting.survey_template_exporter import export_survey
from ecostream.reporting.inventory_template_exporter import export_inventory
from ecostream.reporting.report_template_exporter import export_report

SURVEY_FILE = "Bang_khao_sat_da_dien.xlsx"
INVENTORY_FILE = "GHGs_inventory_da_tinh.xlsx"
REPORT_FILE = "Bao_cao_kiem_ke_KNK.docx"


def _workspace(run_id: str, base_runs_dir: str | None = None) -> BlackboardWorkspace:
    if not run_id or len(run_id) > 96 or not all(c.isascii() and (c.isalnum() or c in "_-") for c in run_id):
        raise SurveyValidationError("Mã phiên chạy không hợp lệ")
    return BlackboardWorkspace(run_id, base_runs_dir)


def _meta(workspace: BlackboardWorkspace):
    path = Path(workspace.run_dir) / "survey_metadata.json"
    if not path.is_file():
        raise SurveyValidationError("Phiên này chưa có biểu khảo sát; hãy tải chứng từ trước")
    return json.loads(path.read_text(encoding="utf-8"))


def prepare_survey(files: list[str], company: str, facility: str, year: int, base_runs_dir: str | None = None) -> dict:
    if not 2000 <= year <= 2100:
        raise SurveyValidationError("Năm báo cáo không hợp lệ")
    if not files:
        raise SurveyValidationError("Cần ít nhất một chứng từ")
    run_id = "survey_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_") + secrets.token_hex(4)
    workspace = _workspace(run_id, base_runs_dir)
    state = workspace.initialize_workspace()
    state.phase, state.progress_pct = PipelinePhase.INGESTED, 12.0
    workspace.save_state(state)
    data = extract_documents(files, year)
    manifest = []
    for path in files:
        name = Path(path).name
        count = sum(1 for item in data.items if item.source_document == name)
        manifest.append({"filename": name, "records": count, "status": "đã dùng để điền khảo sát" if count else "chưa dùng — cần rà soát"})
        workspace.store_raw_input(path)
    if not data.items:
        data.warnings.append("Không có số liệu Scope 1/2 hợp lệ; tải biểu khảo sát về để điền thủ công trước khi tính")
    survey_path = Path(workspace.deliverables_dir) / SURVEY_FILE
    warnings = export_survey(data, str(survey_path), facility, company)
    metadata = {"company": company, "facility": facility, "year": year, "files": manifest, "warnings": warnings}
    (Path(workspace.run_dir) / "survey_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    workspace.save_intermediate_json("survey_extracted.json", [item.__dict__ for item in data.items])
    workspace.save_intermediate_json("survey_warnings.json", warnings)
    state.phase, state.progress_pct, state.active_agent = PipelinePhase.INDEXED, 40.0, None
    workspace.save_state(state)
    return {"run_id": run_id, "stage": "REVIEW_SURVEY", "files": manifest, "warnings": warnings,
            "items": [item.__dict__ for item in data.items], "survey_url": f"/api/survey/runs/{run_id}/survey"}


def _records(data: SurveyData, year: int) -> list[ActivityRecord]:
    db = get_factor_database()
    factor_ids = {"diesel": "EF-SCOPE1-DIESEL", "petrol": "EF-SCOPE1-PETROL", "lpg": "EF-SCOPE1-LPG",
                  "fo": "EF-SCOPE1-FO", "anthracite": "EF-SCOPE1-COAL", "bituminous": "EF-SCOPE1-COAL",
                  "subbituminous": "EF-SCOPE1-COAL", "naturalgas": "EF-SCOPE1-NATURAL-GAS", "electricity": "EF-SCOPE2-VN-GRID"}
    records = []
    for i, item in enumerate(data.items, 1):
        factor = db.get(factor_ids[item.kind])
        if factor is None or factor.unit != item.unit:
            raise SurveyValidationError(f"{item.sheet}!{item.coordinate}: không có hệ số phù hợp")
        if item.kind == "electricity":
            scope, category, desc = EmissionScope.SCOPE_2, ActivityCategory.PURCHASED_ELECTRICITY, "Điện lưới EVN"
        else:
            scope = EmissionScope.SCOPE_1
            category = ActivityCategory.MOBILE_COMBUSTION if item.sheet == "1.2" else ActivityCategory.STATIONARY_COMBUSTION
            desc = FUEL_NAMES[item.kind]
        records.append(ActivityRecord(
            id=f"SURVEY-{i:04d}", description=f"{desc} tháng {item.month:02d}/{year}", scope=scope,
            category=category, quantity=item.quantity, unit=item.unit, date=f"{year}-{item.month:02d}-01",
            measurement_type=MeasurementType.ESTIMATED_ACTIVITY,
            evidence=EvidenceProvenance(source_document=item.source_document, document_type="SURVEY_WORKBOOK",
                page_or_line=f"{item.sheet}!{item.coordinate}", snippet=item.source_location,
                extraction_method="SURVEY_REVIEW", extraction_confidence=0.75),
            quality=DataQualityIndicator(completeness_score=0.80, temporal_score=0.90,
                geographical_score=0.85, source_reliability_score=0.70, extraction_confidence_score=0.75),
        ))
    return records


def calculate_survey(run_id: str, reviewed_file: str | None = None, base_runs_dir: str | None = None) -> dict:
    workspace = _workspace(run_id, base_runs_dir)
    metadata = _meta(workspace)
    source = reviewed_file or str(Path(workspace.deliverables_dir) / SURVEY_FILE)
    data = read_survey(source, source_name=SURVEY_FILE)
    records = _records(data, metadata["year"])
    original_items = workspace.load_intermediate_json("survey_extracted.json") or []
    original_cells = {(i["sheet"], i["coordinate"]): i for i in original_items if i["coordinate"]}
    if reviewed_file:
        for item in data.items:
            original = original_cells.get((item.sheet, item.coordinate))
            if not original or original["quantity"] != item.quantity:
                item.estimated = True
    calculator = CarbonCalculator()
    calculations = calculator.calculate_all(records)
    scopes, total, lower, upper = calculator.aggregate_scopes(calculations)
    reliability = ReliabilityEngine.evaluate(records)
    summary = CarbonAdvisor.compile_summary(
        company_name=metadata["company"], facility_location=metadata["facility"], reporting_period=str(metadata["year"]),
        industry_sector="Chưa xác nhận", records=records, calculations=calculations, scopes=scopes,
        total_tonnes=total, total_min=lower, total_max=upper, reliability=reliability,
    )
    summary.uncalculated_sources = [
        "Các nguồn Scope 1/2 ngoài nhiên liệu đã ánh xạ và điện lưới (môi chất lạnh, quá trình công nghiệp, nước thải, nhiệt/hơi mua ngoài) chưa được xử lý từ biểu khảo sát",
        "Scope 3 không nằm trong phạm vi luồng này",
    ]
    report = AuditReport(report_id="SURVEY-" + run_id, generated_at=datetime.now(timezone.utc).isoformat(),
        summary=summary, calculations=calculations)
    target = Path(workspace.deliverables_dir)
    warnings = list(metadata["warnings"]) + data.warnings
    factor_years = {get_factor_database().get(fid).year for fid in (
        "EF-SCOPE1-DIESEL", "EF-SCOPE1-PETROL", "EF-SCOPE1-LPG", "EF-SCOPE1-COAL",
        "EF-SCOPE1-FO", "EF-SCOPE1-NATURAL-GAS", "EF-SCOPE2-VN-GRID")}
    if metadata["year"] not in factor_years:
        warnings.append(f"Hệ số phát thải có niên độ {sorted(factor_years)}, khác năm báo cáo {metadata['year']}; cần xác nhận hệ số hiện hành")
    if not any(item.kind == "electricity" for item in data.items):
        warnings.append("Chưa có điện mua lưới; Scope 2 không được kết luận là bằng 0")
    if not any(item.kind != "electricity" for item in data.items):
        warnings.append("Chưa có nhiên liệu; Scope 1 không được kết luận là bằng 0")
    if len({item.month for item in data.items if item.kind == "electricity"}) != 12:
        warnings.append("Dữ liệu điện chưa đủ 12 tháng; không nội suy ngầm")
    # Build and validate all outputs before publishing them to a run. A failed
    # workbook/report export must not replace the survey or completed outputs.
    with tempfile.TemporaryDirectory(prefix="survey_export_") as stage_dir:
        staged = Path(stage_dir)
        warnings += export_inventory(data, report, str(staged / INVENTORY_FILE))
        export_report(report, str(staged / REPORT_FILE), metadata["files"], warnings)
        (staged / "final_inventory_summary.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
        if reviewed_file:
            import shutil
            shutil.copy2(reviewed_file, staged / SURVEY_FILE)
        for filename in (INVENTORY_FILE, REPORT_FILE, "final_inventory_summary.json") + ((SURVEY_FILE,) if reviewed_file else ()):
            os.replace(staged / filename, target / filename)
    workspace.save_intermediate_json("survey_validated.json", [item.__dict__ for item in data.items])
    workspace.save_intermediate_json("survey_warnings.json", warnings)
    if reviewed_file:
        metadata["reviewed"] = True
        (Path(workspace.run_dir) / "survey_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    state = workspace.load_state()
    state.phase, state.progress_pct, state.end_time = PipelinePhase.COMPLETED, 100.0, datetime.now(timezone.utc).isoformat()
    workspace.save_state(state)
    return {"run_id": run_id, "stage": "COMPLETED", "summary": summary.model_dump(mode="json"),
            "calculations": [c.model_dump(mode="json") for c in calculations], "warnings": warnings,
            "deliverables": {"survey": SURVEY_FILE, "inventory": INVENTORY_FILE, "docx": REPORT_FILE}}


def get_survey_status(run_id: str, base_runs_dir: str | None = None) -> dict:
    workspace = _workspace(run_id, base_runs_dir)
    metadata = _meta(workspace)
    return {"run_id": run_id, "stage": "COMPLETED" if (Path(workspace.deliverables_dir) / REPORT_FILE).exists() else "REVIEW_SURVEY", **metadata}
