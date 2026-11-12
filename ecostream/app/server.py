"""FastAPI web service serving the EcoStream Interactive Carbon & Reliability Dashboard with Multi-Agent Orchestrator."""

import os
import sys
import shutil
import tempfile
import socket
from datetime import datetime
from typing import Dict, List, Optional
import json
import hashlib
from pydantic import BaseModel

# Configure UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import re
import secrets
import uvicorn
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles

from ecostream.orchestrator.pipeline import WorkflowOrchestrator
from ecostream.orchestrator.state import BlackboardWorkspace
from ecostream.models.results import AuditReport
from ecostream.reporting.export import ReportExporter
from ecostream.factors.database import get_factor_database

app = FastAPI(
    title="EcoStream Multi-Agent AI Carbon Engine",
    description="Multi-agent carbon accounting, Decree 06/2022 Mẫu 02 mitigation, and audit query/assumption logs.",
    version="0.2.0",
)

# ── 1. Hardened CORS Configuration ────────────────────────────────────
# Restrict CORS to authorized internal and configured local domains
allowed_origins_env = os.environ.get("ECOSTREAM_ALLOWED_ORIGINS", "")
if allowed_origins_env:
    allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
else:
    allowed_origins = [
        "http://localhost",
        "http://localhost:8000",
        "http://localhost:3000",
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ── 2. Path Traversal Guard Utilities ─────────────────────────────────
def _validate_safe_identifier(name: str, field_name: str = "identifier") -> str:
    """Validate that identifier does not contain directory traversal characters."""
    if not name or not re.match(r"^[a-zA-Z0-9_\-\.]+$", name) or ".." in name or "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}: Path traversal detected.")
    return name

def _verify_safe_path(base_dir: str, filename: str) -> str:
    """Ensure target path resides strictly inside base_dir using os.path.commonpath."""
    _validate_safe_identifier(filename, "filename")
    abs_base = os.path.abspath(base_dir)
    target_path = os.path.abspath(os.path.join(base_dir, filename))
    if os.path.commonpath([abs_base, target_path]) != abs_base:
        raise HTTPException(status_code=403, detail="Forbidden: Path Traversal attempt blocked.")
    return target_path

# ── 3. API Key Authentication Guard ───────────────────────────────────
def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    api_key: Optional[str] = Query(None),
) -> bool:
    """Authenticate incoming requests via X-API-Key header or query parameter.

    If ECOSTREAM_API_KEY environment variable is configured, requests must provide
    a matching key. If not configured, access is granted for local development/testing.
    """
    expected_key = os.environ.get("ECOSTREAM_API_KEY")
    if not expected_key:
        return True

    provided = x_api_key or api_key
    if not provided or not secrets.compare_digest(provided, expected_key):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid or missing API Key. Provide valid X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return True

# Locate base directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
SAMPLES_DIR = os.path.join(PROJECT_ROOT, "data", "samples")
RUNS_DIR = os.path.join(PROJECT_ROOT, "runs")

# Cache latest generated report and per-run reports for multi-tenant isolation
_latest_report: Optional[AuditReport] = None
_reports_by_run: Dict[str, AuditReport] = {}

DEFAULT_PRO_KEYS = {"ECO-PRO-2026", "ECO-ENTERPRISE-2026", "USTH-INNO-2026"}


class EnterpriseLoginRequest(BaseModel):
    email: str = "demo@ecogarment.vn"
    org_id: str = "ecogarment-vn"
    license_key: Optional[str] = None


class LicenseVerifyRequest(BaseModel):
    license_key: str


def _get_valid_pro_keys() -> set:
    env_keys = os.environ.get("ECOSTREAM_PRO_KEYS", "")
    custom = {k.strip().upper() for k in env_keys.split(",") if k.strip()}
    return DEFAULT_PRO_KEYS.union(custom)


def _is_valid_pro_key(key: Optional[str]) -> bool:
    if not key:
        return False
    return key.strip().upper() in _get_valid_pro_keys()


def _save_tenant_meta(run_dir: str, org_id: Optional[str], user_id: Optional[str]) -> None:
    if not org_id and not user_id:
        return
    try:
        os.makedirs(run_dir, exist_ok=True)
        meta_path = os.path.join(run_dir, "tenant_meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "org_id": org_id or "public",
                    "user_id": user_id or "anonymous",
                    "created_at": datetime.now().isoformat(),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
    except Exception:
        pass


def _load_tenant_meta(run_dir: str) -> dict:
    meta_path = os.path.join(run_dir, "tenant_meta.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"org_id": "public", "user_id": "anonymous"}


def _resolve_report(run_id: Optional[str] = None) -> AuditReport:
    """Resolve report for a specific run_id (multi-user safe) or fall back to _latest_report."""
    global _latest_report
    if run_id and run_id != "benchmark":
        _validate_safe_identifier(run_id, "run_id")
        if run_id in _reports_by_run:
            return _reports_by_run[run_id]
        workspace = BlackboardWorkspace(run_id, RUNS_DIR)
        deliv_json = os.path.join(workspace.deliverables_dir, "final_inventory_summary.json")
        if os.path.exists(deliv_json):
            with open(deliv_json, "r", encoding="utf-8") as f:
                report_data = json.load(f)
                report_Obj = AuditReport(**report_data)
                _reports_by_run[run_id] = report_Obj
                return report_Obj
    if not _latest_report:
        run_demo()
    return _latest_report

# Mount static files directory if present
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h2>EcoStream Dashboard UI is being loaded...</h2>")


@app.get("/monitor", response_class=HTMLResponse)
def serve_monitor():
    monitor_path = os.path.join(STATIC_DIR, "monitor.html")
    if os.path.exists(monitor_path):
        with open(monitor_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h2>EcoStream Live Workflow Monitor is being loaded...</h2>")


@app.get("/monitor.js")
def serve_monitor_js():
    js_path = os.path.join(STATIC_DIR, "monitor.js")
    if os.path.exists(js_path):
        return FileResponse(js_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="monitor.js not found")




@app.get("/api/auth/status")
def get_auth_status(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    api_key: Optional[str] = Query(None),
):
    """Check API Key authentication status."""
    expected_key = os.environ.get("ECOSTREAM_API_KEY")
    if not expected_key:
        return {"auth_required": False, "authenticated": True, "mode": "development_unrestricted"}
    provided = x_api_key or api_key
    is_valid = bool(provided and secrets.compare_digest(provided, expected_key))
    return {
        "auth_required": True,
        "authenticated": is_valid,
        "mode": "production_secured",
    }


@app.post("/api/auth/login")
def enterprise_login(req: EnterpriseLoginRequest):
    """Authenticate an enterprise user/organization and determine subscription tier (FREE vs PRO)."""
    clean_org = re.sub(r"[^a-zA-Z0-9_\-\.]", "-", req.org_id.strip() or "default-org").strip("-") or "default-org"
    clean_email = req.email.strip() or "user@enterprise.vn"
    user_id = hashlib.sha256(f"{clean_org}:{clean_email}".encode("utf-8")).hexdigest()[:12]
    is_pro = _is_valid_pro_key(req.license_key)
    tier = "PRO" if is_pro else "FREE"
    token_seed = f"{clean_org}:{user_id}:{tier}:{secrets.token_hex(8)}"
    session_token = hashlib.sha256(token_seed.encode("utf-8")).hexdigest()
    return {
        "authenticated": True,
        "email": clean_email,
        "user_id": user_id,
        "org_id": clean_org,
        "tier": tier,
        "is_pro": is_pro,
        "session_token": session_token,
        "features": {
            "watermark_free": is_pro,
            "docx_mau02_export": is_pro,
            "excel_audit_export": is_pro,
        },
    }


@app.post("/api/license/verify")
def verify_license_key(req: LicenseVerifyRequest):
    """Verify whether a provided License Key unlocks Pro/Enterprise features."""
    is_valid = _is_valid_pro_key(req.license_key)
    if not is_valid:
        raise HTTPException(
            status_code=403,
            detail="Mã License không hợp lệ hoặc đã hết hạn. Vui lòng kiểm tra lại (Gợi ý mã trải nghiệm Pro: ECO-PRO-2026).",
        )
    return {
        "valid": True,
        "tier": "PRO",
        "license_key": req.license_key.strip().upper(),
        "message": "Đã kích hoạt thành công gói EcoStream Pro / Enterprise! Toàn bộ báo cáo Word Mẫu 02 & Excel đã được mở khóa.",
    }


@app.get("/api/demo", dependencies=[Depends(verify_api_key)])
def run_demo(
    org_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    x_org_id: Optional[str] = Header(None, alias="X-Org-Id"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
):
    """Run benchmark case study using multi-agent workflow on data/samples/input.xlsx."""
    global _latest_report
    sample_xlsx = os.path.join(SAMPLES_DIR, "input.xlsx")
    if not os.path.exists(sample_xlsx):
        from scripts.generate_mock_excel import generate_benchmark_excel
        generate_benchmark_excel(sample_xlsx)

    orch = WorkflowOrchestrator(offline_mode=True)
    res = orch.run_pipeline(
        input_files=[sample_xlsx],
        company_name="EcoGarment Vietnam JSC",
        facility_name="Nhà máy May & Năng lượng Hà Nam",
        reporting_year=2026,
    )
    eff_org = org_id or x_org_id
    eff_user = user_id or x_user_id
    _save_tenant_meta(orch.workspace.run_dir, eff_org, eff_user)

    # Build backward-compatible AuditReport structure
    deliv_json = os.path.join(orch.workspace.deliverables_dir, "final_inventory_summary.json")
    if os.path.exists(deliv_json):
        with open(deliv_json, "r", encoding="utf-8") as f:
            report_data = json.load(f)
            report_data["run_id"] = orch.run_id
            report_data["org_id"] = eff_org or "public"
            report_obj = AuditReport(**report_data)
            _latest_report = report_obj
            _reports_by_run[orch.run_id] = report_obj
            return report_data

    return res


@app.post("/api/upload", dependencies=[Depends(verify_api_key)])
async def upload_documents(
    files: List[UploadFile] = File(...),
    company: str = Form("EcoGarment Vietnam JSC"),
    period: str = Form("2026"),
    location: str = Form("Nhà máy May & Năng lượng Hà Nam"),
    enable_scope3: bool = Form(False),
    enable_mitigation: bool = Form(False),
    org_id: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
    x_org_id: Optional[str] = Header(None, alias="X-Org-Id"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
):
    """Upload custom business files (Excel, PDF, Word, CSV) and run multi-agent pipeline."""
    global _latest_report

    os.makedirs(RUNS_DIR, exist_ok=True)
    temp_dir = tempfile.mkdtemp()
    saved_paths = []
    try:
        for f in files:
            raw_name = os.path.basename(f.filename or "upload.bin")
            safe_fname = _validate_safe_identifier(raw_name, "upload filename")
            dest_path = _verify_safe_path(temp_dir, safe_fname)
            with open(dest_path, "wb") as out_f:
                content = await f.read()
                out_f.write(content)
            saved_paths.append(dest_path)

        # Parse year if available
        year_num = 2026
        try:
            m = re.search(r"\b(202\d)\b", period)
            if m:
                year_num = int(m.group(1))
        except Exception:
            pass

        eff_org = org_id or x_org_id
        eff_user = user_id or x_user_id
        safe_c = re.sub(r'[^a-zA-Z0-9À-ỹ]+', '-', company).strip('-')
        safe_l = re.sub(r'[^a-zA-Z0-9À-ỹ]+', '-', location).strip('-')
        ts_suffix = datetime.now().strftime("%H%M%S")
        org_prefix = f"{re.sub(r'[^a-zA-Z0-9_-]+', '', eff_org)}_" if eff_org else ""
        run_name = f"{org_prefix}{safe_c}_{safe_l}_{period}_{ts_suffix}"
        orch = WorkflowOrchestrator(run_id=run_name, offline_mode=True)
        res = orch.run_pipeline(
            input_files=saved_paths,
            company_name=company,
            facility_name=location,
            reporting_year=year_num,
            enable_scope3=enable_scope3,
            enable_mitigation=enable_mitigation,
        )
        _save_tenant_meta(orch.workspace.run_dir, eff_org, eff_user)

        deliv_json = os.path.join(orch.workspace.deliverables_dir, "final_inventory_summary.json")
        if os.path.exists(deliv_json):
            with open(deliv_json, "r", encoding="utf-8") as f:
                report_data = json.load(f)
                report_data["run_id"] = orch.run_id
                report_data["org_id"] = eff_org or "public"
                report_obj = AuditReport(**report_data)
                _latest_report = report_obj
                _reports_by_run[orch.run_id] = report_obj
                return report_data

        return res
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        return {"error": "Pipeline Crashed", "details": err_msg}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.get("/api/orchestrator/runs")
def list_runs(
    org_id: Optional[str] = Query(None),
    x_org_id: Optional[str] = Header(None, alias="X-Org-Id"),
):
    """List pipeline execution runs in blackboard workspace (supports multi-tenant org_id isolation)."""
    if not os.path.exists(RUNS_DIR):
        return {"runs": []}
    filter_org = org_id or x_org_id
    runs = []
    for r_name in sorted(os.listdir(RUNS_DIR), reverse=True):
        r_dir = os.path.join(RUNS_DIR, r_name)
        if os.path.isdir(r_dir):
            tenant_meta = _load_tenant_meta(r_dir)
            if filter_org and tenant_meta.get("org_id") not in (filter_org, "public"):
                continue
            workspace = BlackboardWorkspace(r_name, RUNS_DIR)
            state = workspace.load_state()
            queries = workspace.load_intermediate_json("query_log.json") or []
            assumptions = workspace.load_intermediate_json("assumption_log.json") or []
            deliverables = workspace.list_deliverables()
            intermediate_files = workspace.list_intermediate_files()

            runs.append({
                "run_id": r_name,
                "org_id": tenant_meta.get("org_id", "public"),
                "user_id": tenant_meta.get("user_id", "anonymous"),
                "state": state.model_dump() if state else None,
                "phase": state.phase.value if state else "UNKNOWN",
                "progress_pct": state.progress_pct if state else 0.0,
                "start_time": state.start_time if state else None,
                "end_time": state.end_time if state else None,
                "queries_count": len(queries),
                "assumptions_count": len(assumptions),
                "deliverables_count": len(deliverables),
                "intermediate_count": len(intermediate_files),
                "has_deliverables": len(deliverables) > 0,
            })
    return {"runs": runs}


@app.get("/api/orchestrator/runs/{run_id}", dependencies=[Depends(verify_api_key)])
def get_run_details(run_id: str):
    """Get state, index, intermediate extractions, logs, and deliverables for a specific run."""
    _validate_safe_identifier(run_id, "run_id")
    workspace = BlackboardWorkspace(run_id, RUNS_DIR)
    state = workspace.load_state()
    if not state:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found.")

    index = workspace.load_index()
    scope1 = workspace.load_intermediate_json("scope1_extracted.json")
    scope2 = workspace.load_intermediate_json("scope2_extracted.json")
    scope3 = workspace.load_intermediate_json("scope3_extracted.json")
    mitigation = workspace.load_intermediate_json("mitigation_extracted.json")
    math_results = workspace.load_intermediate_json("math_results.json")
    mitigation_summary = workspace.load_intermediate_json("mitigation_summary.json")
    queries = workspace.load_intermediate_json("query_log.json")
    assumptions = workspace.load_intermediate_json("assumption_log.json")
    intermediate_files = workspace.list_intermediate_files()
    deliverables = workspace.list_deliverables()
    manifest = workspace.get_file_manifest()

    return {
        "run_id": run_id,
        "state": state.model_dump(),
        "index": index.model_dump() if index else None,
        "intermediate": {
            "scope1": scope1 or [],
            "scope2": scope2 or [],
            "scope3": scope3 or [],
            "mitigation": mitigation or [],
            "math_results": math_results,
            "mitigation_summary": mitigation_summary,
            "queries": queries or [],
            "assumptions": assumptions or [],
        },
        "intermediate_files": intermediate_files,
        "deliverables": deliverables,
        "manifest": manifest,
        "math_results": math_results,
        "mitigation_summary": mitigation_summary,
        "queries": queries or [],
        "assumptions": assumptions or [],
    }


@app.get("/api/orchestrator/runs/{run_id}/files", dependencies=[Depends(verify_api_key)])
def get_run_files(run_id: str):
    """Get directory tree manifest for a specific run."""
    _validate_safe_identifier(run_id, "run_id")
    workspace = BlackboardWorkspace(run_id, RUNS_DIR)
    if not os.path.exists(workspace.run_dir):
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found.")
    return workspace.get_file_manifest()


@app.get("/api/orchestrator/runs/{run_id}/intermediate/{filename}", dependencies=[Depends(verify_api_key)])
def get_intermediate_file(run_id: str, filename: str):
    """Fetch raw intermediate JSON/text file."""
    _validate_safe_identifier(run_id, "run_id")
    workspace = BlackboardWorkspace(run_id, RUNS_DIR)
    fpath = _verify_safe_path(workspace.intermediate_dir, filename)
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail=f"Intermediate file {filename} not found in run {run_id}.")

    if filename.endswith(".json"):
        with open(fpath, "r", encoding="utf-8") as f:
            import json
            return json.load(f)
    return FileResponse(fpath, media_type="text/plain; charset=utf-8", filename=filename)



@app.get("/api/orchestrator/runs/{run_id}/deliverables/{filename}", dependencies=[Depends(verify_api_key)])
def download_deliverable(run_id: str, filename: str):
    """Download a generated deliverable file (.md, .html, .docx, .pdf, .json)."""
    _validate_safe_identifier(run_id, "run_id")
    workspace = BlackboardWorkspace(run_id, RUNS_DIR)
    fpath = _verify_safe_path(workspace.deliverables_dir, filename)
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail=f"Deliverable {filename} not found for run {run_id}.")

    media_type = "application/octet-stream"
    if filename.endswith(".html"):
        media_type = "text/html"
    elif filename.endswith(".md") or filename.endswith(".txt"):
        media_type = "text/markdown; charset=utf-8"
    elif filename.endswith(".json"):
        media_type = "application/json"
    elif filename.endswith(".pdf"):
        media_type = "application/pdf"
    elif filename.endswith(".docx"):
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    return FileResponse(fpath, media_type=media_type, filename=filename)


@app.get("/api/factors")
def list_factors():
    """List all standard emission factors registered in the database."""
    db = get_factor_database()
    return [f.model_dump() for f in db.get_all_factors()]


@app.get("/api/export/html", response_class=HTMLResponse, dependencies=[Depends(verify_api_key)])
@app.get("/api/report/html", response_class=HTMLResponse, dependencies=[Depends(verify_api_key)])
def export_html(
    run_id: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    license_key: Optional[str] = Query(None),
    x_license_key: Optional[str] = Header(None, alias="X-License-Key"),
):
    report = _resolve_report(run_id)
    eff_key = license_key or x_license_key
    use_watermark = (tier and tier.lower() == "free") and not _is_valid_pro_key(eff_key)
    return HTMLResponse(content=ReportExporter.to_html(report, watermark=bool(use_watermark)))


@app.get("/api/export/markdown", response_class=PlainTextResponse, dependencies=[Depends(verify_api_key)])
@app.get("/api/report/markdown", response_class=PlainTextResponse, dependencies=[Depends(verify_api_key)])
def export_markdown(run_id: Optional[str] = Query(None)):
    report = _resolve_report(run_id)
    return PlainTextResponse(content=ReportExporter.to_markdown(report))


@app.get("/api/export/pdf", dependencies=[Depends(verify_api_key)])
@app.get("/api/report/pdf", dependencies=[Depends(verify_api_key)])
def export_pdf(
    run_id: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    license_key: Optional[str] = Query(None),
    x_license_key: Optional[str] = Header(None, alias="X-License-Key"),
):
    report = _resolve_report(run_id)
    eff_key = license_key or x_license_key
    use_watermark = (tier and tier.lower() == "free") and not _is_valid_pro_key(eff_key)
    pdf_bytes = ReportExporter.to_pdf(report, watermark=bool(use_watermark))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="Bao_cao_kiem_ke_va_giam_nhe_KNK.pdf"'},
    )


@app.get("/api/export/docx", dependencies=[Depends(verify_api_key)])
@app.get("/api/report/docx", dependencies=[Depends(verify_api_key)])
def export_docx(
    run_id: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    license_key: Optional[str] = Query(None),
    x_license_key: Optional[str] = Header(None, alias="X-License-Key"),
):
    eff_key = license_key or x_license_key
    if tier and tier.lower() == "free" and not _is_valid_pro_key(eff_key):
        raise HTTPException(
            status_code=402,
            detail="Yêu cầu nâng cấp gói Pro/Enterprise để tải về file Word Mẫu 02 NĐ 06/2022/NĐ-CP.",
        )
    report = _resolve_report(run_id)
    docx_bytes = ReportExporter.to_docx(report)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="Bao_cao_Mau02_ND06.docx"'},
    )


@app.get("/api/export/excel", dependencies=[Depends(verify_api_key)])
@app.get("/api/report/excel", dependencies=[Depends(verify_api_key)])
def export_excel(
    run_id: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    license_key: Optional[str] = Query(None),
    x_license_key: Optional[str] = Header(None, alias="X-License-Key"),
):
    eff_key = license_key or x_license_key
    if tier and tier.lower() == "free" and not _is_valid_pro_key(eff_key):
        raise HTTPException(
            status_code=402,
            detail="Yêu cầu nâng cấp gói Pro/Enterprise để tải về Hồ sơ kiểm toán Excel.",
        )
    report = _resolve_report(run_id)
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        ReportExporter.to_excel(report, tmp_path)
        with open(tmp_path, "rb") as f:
            excel_bytes = f.read()
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="Ho_so_ket_qua_CO2_EcoStream.xlsx"'},
    )


def find_available_port(start_port: int = 8000, host: str = "127.0.0.1", max_attempts: int = 20) -> int:
    """Find the first available TCP port."""
    for port in range(start_port, start_port + max_attempts):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind((host, port))
            s.close()
            return port
        except Exception:
            continue

    # Fallback to ephemeral port
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, 0))
    port = s.getsockname()[1]
    s.close()
    return port


def run_server(host: Optional[str] = None, port: Optional[int] = None):
    env_port = os.environ.get("PORT")
    env_host = os.environ.get("ECOSTREAM_HOST") or os.environ.get("HOST")
    if env_port:
        actual_host = host or env_host or "0.0.0.0"
        actual_port = int(env_port)
    else:
        actual_host = host or env_host or "127.0.0.1"
        actual_port = find_available_port(port or 8000, actual_host)
    print(f"\n[EcoStream] Multi-Agent Web Server is live at: http://{actual_host}:{actual_port}\n")
    uvicorn.run(app, host=actual_host, port=actual_port)


if __name__ == "__main__":
    run_server()
