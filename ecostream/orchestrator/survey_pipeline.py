"""Three-stage document → reviewable survey → inventory → report workflow."""
from __future__ import annotations

import json
import re
import secrets
import tempfile
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from ecostream.engine.advisor import CarbonAdvisor
from ecostream.engine.calculator import CarbonCalculator
from ecostream.engine.reliability import ReliabilityEngine
from ecostream.factors.database import get_factor_database
from ecostream.ingestion.survey_workbook import (
    FUEL_NAMES, FUEL_ROWS, SURVEY_NAME, TEMPLATES, SurveyData, SurveyGeneralInfo,
    SurveyItem, SurveyValidationError, classify_fuel, extract_documents,
    normalize_quantity, parse_number, read_general_info, read_survey,
)
from ecostream.models.activity import (
    ActivityCategory, ActivityRecord, DataQualityIndicator, EmissionScope,
    EvidenceProvenance, MeasurementType,
)
from ecostream.models.results import AuditReport
from ecostream.models.state import PipelinePhase
from ecostream.orchestrator.state import BlackboardWorkspace
from openpyxl import load_workbook
from ecostream.reporting.survey_template_exporter import (
    apply_general_info, autofit_survey_workbook, export_survey,
)
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


def prepare_survey(
    files: list[str],
    company: str,
    facility: str,
    year: int,
    base_runs_dir: str | None = None,
    general_info: SurveyGeneralInfo | dict | None = None,
) -> dict:
    if not 2000 <= year <= 2100:
        raise SurveyValidationError("Năm báo cáo không hợp lệ")
    if not files:
        raise SurveyValidationError("Cần ít nhất một chứng từ")
    info_obj = (
        SurveyGeneralInfo.from_dict(asdict(general_info))
        if isinstance(general_info, SurveyGeneralInfo)
        else SurveyGeneralInfo.from_dict(general_info)
    )
    if not info_obj.facility_name:
        info_obj.facility_name = facility.strip()
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
        aux_used = any(w.startswith(f"{name}: đã trích xuất đầy đủ") for w in data.warnings)
        status = "đã dùng để điền khảo sát" if (count or aux_used) else "chưa dùng — cần rà soát"
        manifest.append({"filename": name, "records": count, "status": status})
        workspace.store_raw_input(path)
    if not data.items:
        data.warnings.append("Không có số liệu Scope 1/2 hợp lệ; tải biểu khảo sát về để điền thủ công trước khi tính")
    survey_path = Path(workspace.deliverables_dir) / SURVEY_FILE
    warnings = export_survey(data, str(survey_path), facility, company, general_info=info_obj)
    info_dict = asdict(info_obj)
    metadata = {
        "company": company,
        "facility": facility,
        "year": year,
        "general_info": info_dict,
        "files": manifest,
        "warnings": warnings,
    }
    (Path(workspace.run_dir) / "survey_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    workspace.save_intermediate_json("survey_extracted.json", [item.__dict__ for item in data.items])
    workspace.save_intermediate_json("survey_warnings.json", warnings)
    state.phase, state.progress_pct, state.active_agent = PipelinePhase.INDEXED, 40.0, None
    workspace.save_state(state)
    return {"run_id": run_id, "stage": "REVIEW_SURVEY", "files": manifest, "warnings": warnings,
            "general_info": info_dict,
            "items": [item.__dict__ for item in data.items], "survey_url": f"/api/survey/runs/{run_id}/survey"}


def _records(data: SurveyData, year: int) -> list[ActivityRecord]:
    db = get_factor_database()
    factor_ids = {
        "mixed_coal": "EF-SCOPE1-COAL",
        "bituminous": "EF-SCOPE1-COAL",
        "subbituminous": "EF-SCOPE1-COAL",
        "anthracite": "EF-SCOPE1-COAL",
        "diesel": "EF-SCOPE1-DIESEL",
        "fo": "EF-SCOPE1-FO",
        "kerosene": "EF-SCOPE1-DIESEL",
        "petrol": "EF-SCOPE1-PETROL",
        "naturalgas": "EF-SCOPE1-NATURAL-GAS",
        "lpg": "EF-SCOPE1-LPG",
        "lng": "EF-SCOPE1-LPG",
        "biogas": "EF-SCOPE1-NATURAL-GAS",
        "liquid_biofuel": "EF-SCOPE1-PETROL",
        "other_petroleum": "EF-SCOPE1-FO",
        "wood": "EF-SCOPE1-COAL",
        "charcoal": "EF-SCOPE1-COAL",
        "bagasse": "EF-SCOPE1-COAL",
        "rice_husk": "EF-SCOPE1-COAL",
        "straw": "EF-SCOPE1-COAL",
        "other_solid_biomass": "EF-SCOPE1-COAL",
        "industrial_waste": "EF-SCOPE1-COAL",
        "municipal_waste": "EF-SCOPE1-COAL",
        "peat": "EF-SCOPE1-COAL",
        "electricity": "EF-SCOPE2-VN-GRID",
    }
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
    merged_info = dict(metadata.get("general_info") or {})
    if data.general_info is not None:
        for key, value in asdict(data.general_info).items():
            if value:
                merged_info[key] = value
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
    effective_facility = merged_info.get("facility_name") or metadata["facility"]
    effective_sector = merged_info.get("industry_sector") or "Chưa xác nhận"
    summary = CarbonAdvisor.compile_summary(
        company_name=metadata["company"], facility_location=effective_facility, reporting_period=str(metadata["year"]),
        industry_sector=effective_sector, records=records, calculations=calculations, scopes=scopes,
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
        export_report(report, str(staged / REPORT_FILE), metadata["files"], warnings, general_info=merged_info)
        (staged / "final_inventory_summary.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
        survey_updated = False
        if reviewed_file:
            import shutil
            shutil.copy2(reviewed_file, staged / SURVEY_FILE)
            wb_survey = load_workbook(staged / SURVEY_FILE)
            apply_general_info(wb_survey, effective_facility, metadata["company"], merged_info)
            autofit_survey_workbook(wb_survey)
            wb_survey.save(staged / SURVEY_FILE)
            survey_updated = True
        elif (target / SURVEY_FILE).is_file() and any(merged_info.values()):
            import shutil
            shutil.copy2(target / SURVEY_FILE, staged / SURVEY_FILE)
            wb_survey = load_workbook(staged / SURVEY_FILE)
            apply_general_info(wb_survey, effective_facility, metadata["company"], merged_info)
            autofit_survey_workbook(wb_survey)
            wb_survey.save(staged / SURVEY_FILE)
            survey_updated = True
        for filename in (INVENTORY_FILE, REPORT_FILE, "final_inventory_summary.json") + ((SURVEY_FILE,) if survey_updated else ()):
            os.replace(staged / filename, target / filename)
    workspace.save_intermediate_json("survey_validated.json", [item.__dict__ for item in data.items])
    workspace.save_intermediate_json("survey_warnings.json", warnings)
    if reviewed_file:
        metadata["reviewed"] = True
        metadata["general_info"] = merged_info
        (Path(workspace.run_dir) / "survey_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    state = workspace.load_state()
    state.phase, state.progress_pct, state.end_time = PipelinePhase.COMPLETED, 100.0, datetime.now(timezone.utc).isoformat()
    workspace.save_state(state)
    return {"run_id": run_id, "stage": "COMPLETED", "summary": summary.model_dump(mode="json"),
            "calculations": [c.model_dump(mode="json") for c in calculations], "warnings": warnings,
            "general_info": merged_info,
            "deliverables": {"survey": SURVEY_FILE, "inventory": INVENTORY_FILE, "docx": REPORT_FILE}}


def get_survey_status(run_id: str, base_runs_dir: str | None = None) -> dict:
    workspace = _workspace(run_id, base_runs_dir)
    metadata = _meta(workspace)
    return {"run_id": run_id, "stage": "COMPLETED" if (Path(workspace.deliverables_dir) / REPORT_FILE).exists() else "REVIEW_SURVEY", **metadata}


_ALLOWED_UNITS_BY_STD = {
    "liter": ["liter", "lít"],
    "kg": ["kg", "tấn"],
    "m3": ["m3"],
}

_EXTRA_SHEET_ORDER = [
    "Phạm vi 1",
    "1.3",
    "1.4",
    "1.5",
    "1.6",
    "Phạm vi 2",
    "2.2",
    "Thông tin bổ sung",
    "Biện pháp giảm thiểu",
    "Cung cap thong tin khai khoang",
]
_READONLY_EXTRA_SHEETS = {"Phạm vi 1", "Phạm vi 2"}
_EXTRA_SHEET_BOUNDS = {
    "Phạm vi 1": (1, 1, 8, 3),
    "1.3": (1, 2, 8, 6),
    "1.4": (1, 2, 9, 29),
    "1.5": (1, 2, 21, 49),
    "1.6": (1, 2, 36, 48),
    "Phạm vi 2": (1, 2, 4, 4),
    "2.2": (1, 2, 19, 8),
    "Thông tin bổ sung": (1, 2, 10, 4),
    "Biện pháp giảm thiểu": (1, 2, 20, 8),
    "Cung cap thong tin khai khoang": (1, 1, 10, 7),
}


def _optional_number(value, coordinate: str):
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None
    if isinstance(value, str) and value.startswith("="):
        return None
    return parse_number(value, coordinate)


def _safe_str(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_excel_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text[0] in ("=", "+", "-", "@"):
        return f"'{text}"
    return text


def _serialize_extra_sheet(ws, tpl_ws, sheet_name: str) -> dict:
    min_r, min_c, max_r, max_c = _EXTRA_SHEET_BOUNDS[sheet_name]
    merge_spans = {}
    merged_slaves = set()
    for m_range in tpl_ws.merged_cells.ranges:
        if m_range.min_row < min_r or m_range.min_col < min_c or m_range.max_row > max_r or m_range.max_col > max_c:
            # Clamp merges intersecting the active bounding box
            r1 = max(m_range.min_row, min_r)
            c1 = max(m_range.min_col, min_c)
            r2 = min(m_range.max_row, max_r)
            c2 = min(m_range.max_col, max_c)
            if r1 > r2 or c1 > c2:
                continue
        else:
            r1, c1, r2, c2 = m_range.min_row, m_range.min_col, m_range.max_row, m_range.max_col
        merge_spans[(r1, c1)] = (r2 - r1 + 1, c2 - c1 + 1)
        for rr in range(r1, r2 + 1):
            for cc in range(c1, c2 + 1):
                if (rr, cc) != (r1, c1):
                    merged_slaves.add((rr, cc))

    # Compute responsive width tier per column based on headers, active rows, and template width
    from openpyxl.utils import get_column_letter as _col_letter
    _note_prefixes = ("ghi chú", "note:", "* lưu ý", "vui lòng", "nhu cầu kỵ khí")
    col_tiers = {}
    for c in range(min_c, max_c + 1):
        col_w = tpl_ws.column_dimensions[_col_letter(c)].width or 12.0
        max_len = 0
        header_txt = ""
        for r in range(min_r, max_r + 1):
            if (r, c) in merged_slaves:
                continue
            rowspan, colspan = merge_spans.get((r, c), (1, 1))
            if colspan > 1:
                continue
            v = ws.cell(r, c).value
            tv = tpl_ws.cell(r, c).value
            s = str(v if v is not None else (tv if tv is not None else "")).strip()
            if s.casefold().startswith(_note_prefixes):
                continue
            if r <= 3 and s:
                header_txt += " " + s.casefold()
            if s and not s.startswith("="):
                max_len = max(max_len, max((len(line) for line in s.splitlines()), default=0))
        hdr_words = set(re.findall(r"[a-zA-ZÀ-ỹ0-9]+", header_txt)) if "re" in globals() else set(header_txt.split())
        is_narrow_hdr = (
            bool(hdr_words & {"stt", "tt", "unit", "2020", "2022", "tổng"})
            or "đơn vị" in header_txt
            or "mã vật tư" in header_txt
            or "tháng " in header_txt
        )
        is_wide_hdr = any(k in header_txt for k in ("mô tả", "đặc điểm", "thuyết minh", "ghi chú", "tỷ lệ", "thông tin bổ sung", "công nghệ", "tên sản phẩm", "tên biện pháp", "loại khoáng sản", "loại nhiên liệu"))
        if is_narrow_hdr and not is_wide_hdr:
            col_tiers[c] = "narrow"
        elif is_wide_hdr or max_len >= 28 or col_w >= 26:
            col_tiers[c] = "wide"
        elif max_len <= 12 and col_w <= 14:
            col_tiers[c] = "narrow"
        else:
            col_tiers[c] = "medium"

    read_only_sheet = sheet_name in _READONLY_EXTRA_SHEETS
    rows = []
    for r in range(min_r, max_r + 1):
        row_cells = []
        for c in range(min_c, max_c + 1):
            if (r, c) in merged_slaves:
                continue
            cell = ws.cell(r, c)
            tpl_cell = tpl_ws.cell(r, c)
            rowspan, colspan = merge_spans.get((r, c), (1, 1))
            tpl_val = tpl_cell.value
            val = cell.value
            is_formula = isinstance(tpl_val, str) and tpl_val.startswith("=")
            if not is_formula and isinstance(val, str) and val.startswith("="):
                is_formula = True

            if read_only_sheet or is_formula:
                editable = False
            elif tpl_val is None or str(tpl_val).strip() == "…":
                # Keep bottom note rows / empty spacer rows read-only where appropriate
                editable = not (sheet_name == "1.3" and r >= 7) and not (sheet_name == "1.4" and r >= 7) and not (sheet_name == "1.5" and r >= 12) and not (sheet_name == "2.2" and r >= 17) and not (sheet_name == "Thông tin bổ sung" and r >= 9) and not (sheet_name == "Biện pháp giảm thiểu" and r in (3, 9, 14, 19, 20)) and not (sheet_name == "Cung cap thong tin khai khoang" and r >= 10)
            elif sheet_name == "1.5" and isinstance(tpl_val, (int, float)) and c >= 36 and r >= 4:
                editable = True
            else:
                editable = False

            display_val = "" if val is None else ("" if is_formula else str(val))
            is_unmerged_footer_note = (
                colspan == 1
                and rowspan == 1
                and not editable
                and display_val.casefold().startswith(("note:", "vui lòng", "* lưu ý", "nhu cầu kỵ khí"))
                and all(ws.cell(r, cc).value is None for cc in range(c + 1, max_c + 1))
            )
            eff_colspan = (max_c - c + 1) if is_unmerged_footer_note else colspan
            row_cells.append({
                "coord": cell.coordinate,
                "rowspan": rowspan,
                "colspan": eff_colspan,
                "value": display_val,
                "formula": str(val) if is_formula else "",
                "is_header": (r <= 2) or (r == 3 and sheet_name in ("1.1", "1.2", "1.4", "1.5", "2.2", "Cung cap thong tin khai khoang")) or (sheet_name == "Biện pháp giảm thiểu" and r in (3, 9, 14)),
                "editable": editable,
                "col_tier": "wide" if eff_colspan > 3 else col_tiers.get(c, "medium"),
            })
            if is_unmerged_footer_note:
                break
        if row_cells:
            rows.append(row_cells)

    return {
        "name": sheet_name,
        "read_only": read_only_sheet,
        "rows": rows,
    }


def get_survey_workbook_data(run_id: str, base_runs_dir: str | None = None) -> dict:
    """Read ALL sheets, rows, and columns (filled and unfilled) from Bang_khao_sat_da_dien.xlsx."""
    workspace = _workspace(run_id, base_runs_dir)
    metadata = _meta(workspace)
    survey_path = Path(workspace.deliverables_dir) / SURVEY_FILE
    if not survey_path.is_file():
        raise SurveyValidationError("Chưa có tệp biểu khảo sát trong phiên này")
    book = load_workbook(survey_path, data_only=False)
    tpl_book = load_workbook(TEMPLATES / SURVEY_NAME, data_only=False)
    for required in ("Thông tin chung", "1.1", "1.2", "2.1"):
        if required not in book:
            raise SurveyValidationError(f"Thiếu sheet {required!r} trong biểu khảo sát")

    gi_sheet = asdict(read_general_info(book["Thông tin chung"]))
    gi_meta = dict(metadata.get("general_info") or {})
    merged_gi = {k: (gi_sheet.get(k) or gi_meta.get(k) or "") for k in SurveyGeneralInfo.__dataclass_fields__}

    ws_1_1 = book["1.1"]
    tpl_1_1 = tpl_book["1.1"]
    calculable_rows = {row_idx: (kind, std_unit) for kind, (row_idx, _, std_unit) in FUEL_ROWS.items()}
    sheet_1_1 = []
    for row_idx in range(4, 27):
        kind, std_unit = calculable_rows.get(row_idx, ("", ""))
        months = []
        for m in range(1, 13):
            val = ws_1_1.cell(row_idx, m + 5).value
            try:
                months.append(_optional_number(val, f"1.1!{ws_1_1.cell(row_idx, m + 5).coordinate}"))
            except SurveyValidationError:
                months.append(None)
        raw_name = _safe_str(ws_1_1[f"C{row_idx}"].value)
        tpl_name = _safe_str(tpl_1_1[f"C{row_idx}"].value)
        display_name = raw_name or (FUEL_NAMES[kind] if kind else tpl_name)
        unit_val = _safe_str(ws_1_1[f"E{row_idx}"].value) or std_unit
        sheet_1_1.append({
            "stt": ws_1_1[f"B{row_idx}"].value or (row_idx - 3),
            "row": row_idx,
            "kind": kind,
            "calculable": bool(kind),
            "name": display_name,
            "name_editable": row_idx in (7, 17, 23, 26),
            "material_code": _safe_str(ws_1_1[f"D{row_idx}"].value),
            "unit": unit_val,
            "allowed_units": _ALLOWED_UNITS_BY_STD.get(std_unit, []) if std_unit else [],
            "months": months,
            "heating_value": _safe_str(ws_1_1[f"S{row_idx}"].value),
            "equipment": _safe_str(ws_1_1[f"T{row_idx}"].value),
            "supplier": _safe_str(ws_1_1[f"U{row_idx}"].value),
        })

    ws_1_2 = book["1.2"]
    sheet_1_2 = []
    for row_idx in range(4, 22):
        fuel_name = _safe_str(ws_1_2[f"C{row_idx}"].value)
        unit_val = _safe_str(ws_1_2[f"E{row_idx}"].value)
        mat_code = _safe_str(ws_1_2[f"D{row_idx}"].value)
        months = []
        for m in range(1, 13):
            val = ws_1_2.cell(row_idx, m + 5).value
            try:
                num = _optional_number(val, f"1.2!{ws_1_2.cell(row_idx, m + 5).coordinate}")
            except SurveyValidationError:
                num = None
            months.append(num)
        kind = classify_fuel(fuel_name) or ""
        sheet_1_2.append({
            "stt": ws_1_2[f"B{row_idx}"].value or (row_idx - 3),
            "row": row_idx,
            "kind": kind,
            "name": fuel_name,
            "material_code": mat_code,
            "unit": unit_val or (FUEL_ROWS[kind][2] if kind else ""),
            "months": months,
            "heating_value": _safe_str(ws_1_2[f"S{row_idx}"].value),
            "vehicle_type": _safe_str(ws_1_2[f"T{row_idx}"].value),
            "vehicle_info": _safe_str(ws_1_2[f"U{row_idx}"].value),
            "distance_km": _safe_str(ws_1_2[f"V{row_idx}"].value),
            "supplier": _safe_str(ws_1_2[f"W{row_idx}"].value),
        })

    ws_2_1 = book["2.1"]
    sheet_2_1 = []
    for m in range(1, 13):
        row_idx = m + 2
        try:
            grid_kwh = _optional_number(ws_2_1[f"E{row_idx}"].value, f"2.1!E{row_idx}")
        except SurveyValidationError:
            grid_kwh = None
        try:
            self_kwh = _optional_number(ws_2_1[f"F{row_idx}"].value, f"2.1!F{row_idx}")
        except SurveyValidationError:
            self_kwh = None
        sheet_2_1.append({
            "month": m,
            "row": row_idx,
            "material_code": _safe_str(ws_2_1[f"C{row_idx}"].value),
            "unit": _safe_str(ws_2_1[f"D{row_idx}"].value) or "kWh",
            "grid_kwh": grid_kwh,
            "self_kwh": self_kwh,
        })

    extra_sheets = {}
    for sheet_name in _EXTRA_SHEET_ORDER:
        if sheet_name in book and sheet_name in tpl_book:
            extra_sheets[sheet_name] = _serialize_extra_sheet(book[sheet_name], tpl_book[sheet_name], sheet_name)

    mobile_fuel_options = [
        {"kind": kind, "name": FUEL_NAMES[kind], "default_unit": FUEL_ROWS[kind][2],
         "allowed_units": _ALLOWED_UNITS_BY_STD.get(FUEL_ROWS[kind][2], [FUEL_ROWS[kind][2]])}
        for kind in ("diesel", "petrol", "lpg", "naturalgas")
    ]
    return {
        "run_id": run_id,
        "company": metadata.get("company", ""),
        "facility": metadata.get("facility", ""),
        "year": metadata.get("year", 2026),
        "files": metadata.get("files", []),
        "warnings": metadata.get("warnings", []),
        "general_info": merged_gi,
        "sheet_1_1": sheet_1_1,
        "sheet_1_2": sheet_1_2,
        "sheet_2_1": sheet_2_1,
        "extra_sheets": extra_sheets,
        "extra_sheet_order": [s for s in _EXTRA_SHEET_ORDER if s in extra_sheets],
        "mobile_fuel_options": mobile_fuel_options,
    }


def save_survey_workbook_data(run_id: str, payload: dict, base_runs_dir: str | None = None) -> dict:
    """Validate and save user edits from Step 3 directly into Bang_khao_sat_da_dien.xlsx."""
    import shutil

    workspace = _workspace(run_id, base_runs_dir)
    metadata = _meta(workspace)
    survey_path = Path(workspace.deliverables_dir) / SURVEY_FILE
    if not survey_path.is_file():
        raise SurveyValidationError("Chưa có tệp biểu khảo sát trong phiên này")

    with tempfile.TemporaryDirectory(prefix="survey_edit_") as stage_dir:
        staged = Path(stage_dir) / SURVEY_FILE
        shutil.copy2(survey_path, staged)
        book = load_workbook(staged)
        tpl_book = load_workbook(TEMPLATES / SURVEY_NAME, data_only=False)

        # 1. Update Thông tin chung
        raw_gi = payload.get("general_info")
        if isinstance(raw_gi, dict):
            gi_obj = SurveyGeneralInfo.from_dict(raw_gi)
            if not gi_obj.facility_name:
                gi_obj.facility_name = metadata.get("facility", "")
            effective_company = str(payload.get("company") or metadata.get("company") or gi_obj.facility_name).strip()
            effective_facility = gi_obj.facility_name or metadata.get("facility", "")
            apply_general_info(book, effective_facility, effective_company, gi_obj)
            metadata["general_info"] = asdict(gi_obj)
            metadata["facility"] = effective_facility
            if effective_company:
                metadata["company"] = effective_company

        # 2. Update Sheet 1.1 (all 23 rows + S, T, U columns)
        save_warnings = []
        if isinstance(payload.get("sheet_1_1"), list):
            ws_1_1 = book["1.1"]
            row_map = {row_idx: (kind, std_unit) for kind, (row_idx, _, std_unit) in FUEL_ROWS.items()}
            for entry in payload["sheet_1_1"]:
                if not isinstance(entry, dict):
                    continue
                row_idx = int(entry.get("row", 0))
                if not 4 <= row_idx <= 26:
                    continue
                kind, std_unit = row_map.get(row_idx, ("", ""))
                mat_code = _safe_str(entry.get("material_code"))
                unit = _safe_str(entry.get("unit")) or std_unit
                months = entry.get("months") or [None] * 12
                if len(months) != 12:
                    raise SurveyValidationError(f"1.1!{row_idx}: thiếu đủ 12 tháng")
                parsed_months = []
                for m_idx, raw_val in enumerate(months, 1):
                    col_letter = ws_1_1.cell(row_idx, m_idx + 5).coordinate
                    parsed = _optional_number(raw_val, f"1.1!{col_letter}")
                    parsed_months.append(parsed)
                has_any = any(v is not None for v in parsed_months)
                custom_name = _safe_str(entry.get("name"))
                if kind:
                    if row_idx == 7 and custom_name:
                        # Row 7 supports anthracite or a custom coal name
                        matched_coal = classify_fuel(custom_name)
                        if matched_coal == "anthracite":
                            ws_1_1[f"C{row_idx}"] = "Than antraxit (theo chứng từ)"
                            if has_any:
                                normalize_quantity(kind, 1.0, unit, f"1.1!E{row_idx}")
                        else:
                            ws_1_1[f"C{row_idx}"] = _safe_excel_text(custom_name)
                            if has_any:
                                save_warnings.append(f"1.1!C7 ({custom_name}): chưa có hệ số phát thải tự động; đã lưu vào Excel")
                    else:
                        if has_any:
                            normalize_quantity(kind, 1.0, unit, f"1.1!E{row_idx}")
                            if kind == "anthracite":
                                ws_1_1[f"C{row_idx}"] = "Than antraxit (theo chứng từ)"
                else:
                    if row_idx in (7, 17, 23, 26) and custom_name:
                        ws_1_1[f"C{row_idx}"] = _safe_excel_text(custom_name)
                    if has_any:
                        lbl = custom_name or _safe_str(ws_1_1[f"C{row_idx}"].value)
                        save_warnings.append(f"1.1!C{row_idx} ({lbl}): chưa có hệ số phát thải tự động; đã lưu vào Excel")
                ws_1_1[f"D{row_idx}"] = _safe_excel_text(mat_code)
                ws_1_1[f"E{row_idx}"] = _safe_excel_text(unit) if (has_any or entry.get("unit")) else None
                for m_idx, val in enumerate(parsed_months, 1):
                    ws_1_1.cell(row_idx, m_idx + 5).value = val
                ws_1_1[f"R{row_idx}"] = f"=SUM(F{row_idx}:Q{row_idx})" if has_any else None
                if "heating_value" in entry:
                    hv_raw = _safe_str(entry.get("heating_value"))
                    ws_1_1[f"S{row_idx}"] = _optional_number(hv_raw, f"1.1!S{row_idx}") if hv_raw and hv_raw.replace(".", "").replace(",", "").isdigit() else _safe_excel_text(hv_raw)
                if "equipment" in entry:
                    ws_1_1[f"T{row_idx}"] = _safe_excel_text(entry.get("equipment"))
                if "supplier" in entry:
                    ws_1_1[f"U{row_idx}"] = _safe_excel_text(entry.get("supplier"))

        # 3. Update Sheet 1.2 (all 18 rows + S..W columns, including custom fuel names)
        if isinstance(payload.get("sheet_1_2"), list):
            ws_1_2 = book["1.2"]
            for row_idx in range(4, 22):
                for col_idx in (3, 4, 5, 18, 19, 20, 21, 22, 23) + tuple(range(6, 18)):
                    ws_1_2.cell(row_idx, col_idx).value = None
            used_rows = set()
            next_auto_row = 4
            for entry in payload["sheet_1_2"]:
                if not isinstance(entry, dict):
                    continue
                req_row = entry.get("row")
                if req_row is not None and 4 <= int(req_row) <= 21 and int(req_row) not in used_rows:
                    row_idx = int(req_row)
                else:
                    while next_auto_row in used_rows and next_auto_row <= 21:
                        next_auto_row += 1
                    row_idx = next_auto_row
                if row_idx > 21:
                    raise SurveyValidationError("1.2: tối đa 18 dòng nhiên liệu di động")

                fuel_name = _safe_str(entry.get("name"))
                mat_code = _safe_str(entry.get("material_code"))
                hv_raw = _safe_str(entry.get("heating_value"))
                vtype = _safe_str(entry.get("vehicle_type"))
                vinfo = _safe_str(entry.get("vehicle_info"))
                dist = _safe_str(entry.get("distance_km"))
                supp = _safe_str(entry.get("supplier"))
                months = entry.get("months") or [None] * 12
                if len(months) != 12:
                    raise SurveyValidationError("1.2: mỗi dòng cần đủ 12 tháng")
                parsed_months = [
                    _optional_number(raw_val, f"1.2!{ws_1_2.cell(row_idx, m_idx + 5).coordinate}")
                    for m_idx, raw_val in enumerate(months, 1)
                ]
                has_any = any(v is not None for v in parsed_months)
                has_meta = any((fuel_name, mat_code, hv_raw, vtype, vinfo, dist, supp))
                if not has_any and not has_meta:
                    used_rows.add(row_idx)
                    continue

                kind = classify_fuel(fuel_name)
                if has_any and not fuel_name:
                    raise SurveyValidationError(f"1.2!C{row_idx}: thiếu tên loại nhiên liệu")
                if has_any and not kind:
                    save_warnings.append(f"1.2!C{row_idx} ({fuel_name}): nhiên liệu tự nhập, chưa có hệ số phát thải tự động; đã lưu vào Excel")
                unit = _safe_str(entry.get("unit")) or (FUEL_ROWS[kind][2] if kind else "")
                if has_any and kind:
                    normalize_quantity(kind, 1.0, unit, f"1.2!E{row_idx}")

                ws_1_2[f"C{row_idx}"] = FUEL_NAMES[kind] if kind else _safe_excel_text(fuel_name)
                ws_1_2[f"D{row_idx}"] = _safe_excel_text(mat_code)
                ws_1_2[f"E{row_idx}"] = _safe_excel_text(unit)
                for m_idx, val in enumerate(parsed_months, 1):
                    ws_1_2.cell(row_idx, m_idx + 5).value = val
                ws_1_2[f"R{row_idx}"] = f"=SUM(F{row_idx}:Q{row_idx})" if has_any else None
                ws_1_2[f"S{row_idx}"] = _optional_number(hv_raw, f"1.2!S{row_idx}") if hv_raw and hv_raw.replace(".", "").replace(",", "").isdigit() else _safe_excel_text(hv_raw)
                ws_1_2[f"T{row_idx}"] = _safe_excel_text(vtype)
                ws_1_2[f"U{row_idx}"] = _safe_excel_text(vinfo)
                ws_1_2[f"V{row_idx}"] = _optional_number(dist, f"1.2!V{row_idx}") if dist and dist.replace(".", "").replace(",", "").isdigit() else _safe_excel_text(dist)
                ws_1_2[f"W{row_idx}"] = _safe_excel_text(supp)
                used_rows.add(row_idx)

        # 4. Update Sheet 2.1
        if isinstance(payload.get("sheet_2_1"), list):
            ws_2_1 = book["2.1"]
            for entry in payload["sheet_2_1"]:
                if not isinstance(entry, dict):
                    continue
                month = int(entry.get("month", 0))
                if not 1 <= month <= 12:
                    continue
                row_idx = month + 2
                mat_code = _safe_str(entry.get("material_code"))
                grid_kwh = _optional_number(entry.get("grid_kwh"), f"2.1!E{row_idx}")
                self_kwh = _optional_number(entry.get("self_kwh"), f"2.1!F{row_idx}")
                unit = _safe_str(entry.get("unit")) or "kWh"
                if grid_kwh is not None:
                    normalize_quantity("electricity", grid_kwh, unit, f"2.1!E{row_idx}")
                has_any = (grid_kwh is not None) or (self_kwh is not None)
                ws_2_1[f"C{row_idx}"] = _safe_excel_text(mat_code)
                ws_2_1[f"D{row_idx}"] = unit if has_any else None
                ws_2_1[f"E{row_idx}"] = grid_kwh
                ws_2_1[f"F{row_idx}"] = self_kwh
                ws_2_1[f"G{row_idx}"] = f"=SUM(E{row_idx}:F{row_idx})" if has_any else None
            ws_2_1["E15"] = "=SUM(E3:E14)"
            ws_2_1["F15"] = "=SUM(F3:F14)"
            ws_2_1["G15"] = "=SUM(G3:G14)"

        # 5. Update extra sheets (1.3, 1.4, 1.5, 1.6, 2.2, Thông tin bổ sung, Biện pháp giảm thiểu, Khai khoáng)
        extra_cells = payload.get("extra_cells")
        if isinstance(extra_cells, dict):
            for sheet_name, cell_map in extra_cells.items():
                if sheet_name not in _EXTRA_SHEET_BOUNDS or sheet_name in _READONLY_EXTRA_SHEETS:
                    continue
                if sheet_name not in book or not isinstance(cell_map, dict):
                    continue
                ws_extra = book[sheet_name]
                tpl_extra = tpl_book[sheet_name]
                # Determine editable coordinates from _serialize_extra_sheet
                editable_coords = {
                    cell["coord"]
                    for row in _serialize_extra_sheet(ws_extra, tpl_extra, sheet_name)["rows"]
                    for cell in row
                    if cell["editable"]
                }
                for coord, raw_val in cell_map.items():
                    if coord not in editable_coords:
                        continue
                    text_val = _safe_str(raw_val)
                    if not text_val:
                        ws_extra[coord] = None
                    else:
                        try:
                            ws_extra[coord] = parse_number(text_val, f"{sheet_name}!{coord}")
                        except SurveyValidationError:
                            ws_extra[coord] = _safe_excel_text(text_val)

        autofit_survey_workbook(book)
        book.save(staged)
        # Validate calculable cells through read_survey (allow empty items or custom unmapped fuel names on Save)
        try:
            read_survey(str(staged), source_name=SURVEY_FILE)
        except SurveyValidationError as exc:
            msg = str(exc)
            if "chưa có số liệu nhiên liệu hoặc điện" not in msg and "nhiên liệu không hỗ trợ" not in msg:
                raise
        os.replace(staged, survey_path)

    metadata["reviewed"] = True
    (Path(workspace.run_dir) / "survey_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    out = get_survey_workbook_data(run_id, base_runs_dir)
    out["save_warnings"] = save_warnings
    return out

