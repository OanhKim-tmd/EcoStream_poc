"""FastAPI web service: survey-first workflow (chứng từ → biểu khảo sát → Scope 1/2 → kết quả)."""

import json
import os
import re
import secrets
import shutil
import socket
import sys
import tempfile
import zipfile
from datetime import datetime
from typing import List, Optional

from cryptography.fernet import Fernet
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import uvicorn

from ecostream.factors.database import get_factor_database
from ecostream.ingestion.survey_workbook import (
    SURVEY_NAME,
    TEMPLATES,
    SurveyGeneralInfo,
    SurveyValidationError,
)
from ecostream.orchestrator.state import BlackboardWorkspace
from ecostream.orchestrator.survey_pipeline import (
    INVENTORY_FILE,
    REPORT_FILE,
    SURVEY_FILE,
    calculate_survey,
    get_survey_status,
    get_survey_workbook_data,
    prepare_survey,
    save_survey_workbook_data,
)

app = FastAPI(
    title="EcoStream — Kiểm kê khí nhà kính cấp cơ sở",
    description="Luồng khảo sát: chứng từ → biểu khảo sát (rà soát) → Scope 1/2 → workbook kiểm kê và báo cáo Word dự thảo.",
    version="0.3.0",
)

# Resolve project paths for source runs and frozen desktop builds.
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    PROJECT_ROOT = sys._MEIPASS
    BASE_DIR = os.path.join(PROJECT_ROOT, "ecostream")
    STATIC_DIR = os.path.join(BASE_DIR, "app", "static")
    SAMPLES_DIR = os.path.join(PROJECT_ROOT, "data", "samples")
    if sys.platform == "darwin":
        _user_data_root = os.path.expanduser("~/Library/Application Support/EcoStream")
    elif sys.platform == "win32":
        _user_data_root = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "EcoStream")
    else:
        _user_data_root = os.path.expanduser("~/.ecostream")
    RUNS_DIR = os.environ.get("ECOSTREAM_RUNS_DIR", os.path.join(_user_data_root, "runs"))
    os.makedirs(RUNS_DIR, exist_ok=True)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    PROJECT_ROOT = os.path.dirname(BASE_DIR)
    STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    SAMPLES_DIR = os.path.join(PROJECT_ROOT, "data", "samples")
    RUNS_DIR = os.environ.get("ECOSTREAM_RUNS_DIR", os.path.join(PROJECT_ROOT, "runs"))


def _validate_safe_identifier(name: str, field_name: str = "identifier") -> str:
    if not name or not re.fullmatch(r"[a-zA-Z0-9_.-]+", name) or ".." in name or "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}: path traversal detected")
    return name


def _sanitize_upload_filename(raw_filename: str) -> str:
    import unicodedata

    raw = (raw_filename or "").strip()
    if not raw or "/" in raw or "\\" in raw or ".." in raw or "\x00" in raw:
        raise HTTPException(status_code=400, detail="Invalid filename: path traversal detected")
    stem, ext = os.path.splitext(raw)
    normalized = unicodedata.normalize("NFKD", stem.replace("đ", "d").replace("Đ", "D"))
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    stem_clean = re.sub(r"[^a-zA-Z0-9_-]+", "_", normalized).strip("_") or "upload"
    ext_clean = re.sub(r"[^a-zA-Z0-9.]+", "", ext.lower())
    return _validate_safe_identifier(f"{stem_clean}{ext_clean}", "filename")


def _verify_safe_path(base_dir: str, filename: str) -> str:
    _validate_safe_identifier(filename, "filename")
    abs_base = os.path.abspath(base_dir)
    target = os.path.abspath(os.path.join(base_dir, filename))
    if os.path.commonpath([abs_base, target]) != abs_base:
        raise HTTPException(status_code=403, detail="Forbidden: path traversal attempt blocked")
    return target


def verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> bool:
    """Require header authentication whenever an API key is configured."""
    expected_key = os.environ.get("ECOSTREAM_API_KEY")
    if not expected_key:
        return True
    if not x_api_key or not secrets.compare_digest(x_api_key, expected_key):
        raise HTTPException(status_code=401, detail="Unauthorized: provide a valid X-API-Key header", headers={"WWW-Authenticate": "ApiKey"})
    return True


def _save_tenant_meta(run_dir: str, org_id: Optional[str], user_id: Optional[str]) -> None:
    if org_id or user_id:
        os.makedirs(run_dir, exist_ok=True)
        meta_path = os.path.join(run_dir, "tenant_meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({"org_id": org_id or "public", "user_id": user_id or "anonymous"}, f, ensure_ascii=False, indent=2)


def _load_tenant_meta(run_dir: str) -> dict:
    meta_path = os.path.join(run_dir, "tenant_meta.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    return {"org_id": "public", "user_id": "anonymous"}


allowed_origins_env = os.environ.get("ECOSTREAM_ALLOWED_ORIGINS", "")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()] if allowed_origins_env else [
    "http://localhost", "http://localhost:8000", "http://localhost:3000",
    "http://127.0.0.1", "http://127.0.0.1:8000", "http://127.0.0.1:3000",
]
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_credentials=False,
                   allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"])

MAX_SURVEY_FILES = max(1, int(os.environ.get("ECOSTREAM_MAX_SURVEY_FILES", "100")))
MAX_SURVEY_FILE_BYTES = 10 * 1024 * 1024
MAX_SURVEY_TOTAL_BYTES = 50 * 1024 * 1024
MAX_UPLOAD_UNCOMPRESSED_BYTES = 250 * 1024 * 1024
MAX_OFFICE_ARCHIVE_MEMBERS = 20_000
MAX_OFFICE_UNCOMPRESSED_BYTES = 200 * 1024 * 1024
MAX_OFFICE_COMPRESSION_RATIO = 100
UPLOAD_BODY_LIMIT = 52 * 1024 * 1024
_BODY_LIMIT_EXCEPTION = type("BodyLimitExceeded", (Exception,), {})


class UploadBodyLimitMiddleware:
    """Reject oversized upload requests before multipart parsing/spooling."""

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") != "/api/survey/prepare" or scope.get("method") != "POST":
            await self.app(scope, receive, send)
            return
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            declared = self.max_bytes + 1
        if declared > self.max_bytes:
            await self._reject(send)
            return
        total = 0
        exceeded = False

        async def limited_receive():
            nonlocal total, exceeded
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > self.max_bytes:
                    exceeded = True
                    return {"type": "http.disconnect"}
            return message

        async def guarded_send(message):
            if exceeded and message["type"] == "http.response.start":
                raise _BODY_LIMIT_EXCEPTION
            await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except _BODY_LIMIT_EXCEPTION:
            await self._reject(send)

    async def _reject(self, send):
        body = b'{"detail":"Upload request exceeds 52 MB limit"}'
        await send({"type": "http.response.start", "status": 413, "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})


app.add_middleware(UploadBodyLimitMiddleware, max_bytes=UPLOAD_BODY_LIMIT)


def _validate_uploaded_document(path: str, filename: str) -> int:
    """Check signatures and bound Office archive expansion; return uncompressed bytes."""
    ext = os.path.splitext(filename)[1].lower()
    with open(path, "rb") as stream:
        signature = stream.read(8)
    if ext == ".pdf":
        if not signature.startswith(b"%PDF-"):
            raise HTTPException(status_code=422, detail=f"Tệp không phải PDF hợp lệ: {filename}")
        return 0
    if ext == ".csv":
        if b"\x00" in signature:
            raise HTTPException(status_code=422, detail=f"CSV có định dạng nhị phân không hợp lệ: {filename}")
        return 0
    if ext not in (".xlsx", ".docx") or not signature.startswith(b"PK\x03\x04"):
        raise HTTPException(status_code=422, detail=f"Chữ ký tệp không khớp định dạng {ext}: {filename}")
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            total_size = sum(item.file_size for item in members)
            compressed_size = max(1, os.path.getsize(path))
            if (len(members) > MAX_OFFICE_ARCHIVE_MEMBERS or total_size > MAX_OFFICE_UNCOMPRESSED_BYTES
                    or total_size / compressed_size > MAX_OFFICE_COMPRESSION_RATIO):
                raise HTTPException(status_code=413, detail=f"Tệp Office bung quá lớn hoặc nén bất thường: {filename}")
            names = {item.filename for item in members}
            required = {"[Content_Types].xml", "xl/workbook.xml"} if ext == ".xlsx" else {"[Content_Types].xml", "word/document.xml"}
            if not required.issubset(names):
                raise HTTPException(status_code=422, detail=f"Cấu trúc {ext} không hợp lệ: {filename}")
            bad_member = archive.testzip()
            if bad_member:
                raise HTTPException(status_code=422, detail=f"Tệp Office bị hỏng: {filename}")
            return total_size
    except (zipfile.BadZipFile, OSError) as exc:
        raise HTTPException(status_code=422, detail=f"Tệp Office không phải ZIP hợp lệ: {filename}") from exc


# Serve bundled UI assets (offline CSS, fonts, icons).
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h2>EcoStream Dashboard UI is being loaded...</h2>")


@app.get("/monitor", response_class=HTMLResponse, dependencies=[Depends(verify_api_key)])
def serve_monitor():
    path = os.path.join(STATIC_DIR, "monitor.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    raise HTTPException(status_code=404, detail="monitor.html not found")


@app.get("/monitor.js", dependencies=[Depends(verify_api_key)])
def serve_monitor_js():
    path = os.path.join(STATIC_DIR, "monitor.js")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="monitor.js not found")
    return FileResponse(path, media_type="application/javascript")


@app.get("/api/auth/status")
def get_auth_status(x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    expected_key = os.environ.get("ECOSTREAM_API_KEY")
    if not expected_key:
        return {"auth_required": False, "authenticated": True, "mode": "development_unrestricted"}
    valid = bool(x_api_key and secrets.compare_digest(x_api_key, expected_key))
    return {"auth_required": True, "authenticated": valid, "mode": "production_secured"}


@app.post("/api/survey/prepare", dependencies=[Depends(verify_api_key)])
async def prepare_survey_from_documents(
    files: List[UploadFile] = File(...), company: str = Form(...), location: str = Form(...), period: int = Form(...),
    contact_name: str = Form(""), contact_role: str = Form(""), contact_phone: str = Form(""), contact_email: str = Form(""),
    facility_address: str = Form(""), facility_phone: str = Form(""), facility_email: str = Form(""),
    legal_representative: str = Form(""), legal_rep_title: str = Form(""), industry_sector: str = Form(""),
    operating_status: str = Form(""), start_year: str = Form(""), facility_representative: str = Form(""),
):
    if not company.strip() or not location.strip():
        raise HTTPException(status_code=422, detail="Tên doanh nghiệp và cơ sở không được để trống")
    if len(company) > 300 or len(location) > 300:
        raise HTTPException(status_code=422, detail="Tên doanh nghiệp/cơ sở vượt quá 300 ký tự")
    metadata_values = (contact_name, contact_role, contact_phone, contact_email, facility_address, facility_phone,
                       facility_email, legal_representative, legal_rep_title, industry_sector, operating_status,
                       start_year, facility_representative)
    if any(len(value) > 500 for value in metadata_values):
        raise HTTPException(status_code=422, detail="Thông tin cơ sở vượt quá giới hạn độ dài")
    if not files or len(files) > MAX_SURVEY_FILES:
        raise HTTPException(status_code=422, detail=f"Chọn 1–{MAX_SURVEY_FILES} chứng từ")
    general_info = SurveyGeneralInfo(
        contact_name=contact_name.strip(), contact_role=contact_role.strip(), contact_phone=contact_phone.strip(),
        contact_email=contact_email.strip(), facility_name=location.strip(), facility_address=facility_address.strip(),
        facility_phone=facility_phone.strip(), facility_email=facility_email.strip(), legal_representative=legal_representative.strip(),
        legal_rep_title=legal_rep_title.strip(), industry_sector=industry_sector.strip(), operating_status=operating_status.strip(),
        start_year=start_year.strip(), facility_representative=facility_representative.strip(),
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        paths, total_bytes, expanded_bytes = [], 0, 0
        try:
            for file in files:
                name = _sanitize_upload_filename(file.filename or "")
                if os.path.splitext(name)[1].lower() not in (".xlsx", ".csv", ".pdf", ".docx"):
                    raise HTTPException(status_code=422, detail=f"Không hỗ trợ định dạng tệp: {name}")
                destination = _verify_safe_path(temp_dir, name)
                if os.path.exists(destination):
                    raise HTTPException(status_code=422, detail=f"Tệp trùng tên: {name}")
                content = await file.read(MAX_SURVEY_FILE_BYTES + 1)
                if len(content) > MAX_SURVEY_FILE_BYTES:
                    raise HTTPException(status_code=413, detail=f"Tệp quá 10 MB: {name}")
                total_bytes += len(content)
                if total_bytes > MAX_SURVEY_TOTAL_BYTES:
                    raise HTTPException(status_code=413, detail="Tổng dung lượng chứng từ vượt quá 50 MB")
                with open(destination, "wb") as stream:
                    stream.write(content)
                expanded_bytes += _validate_uploaded_document(destination, name)
                if expanded_bytes > MAX_UPLOAD_UNCOMPRESSED_BYTES:
                    raise HTTPException(status_code=413, detail="Tổng dữ liệu Office sau giải nén vượt quá 250 MB")
                paths.append(destination)
            return prepare_survey(paths, company.strip(), location.strip(), period, RUNS_DIR, general_info=general_info)
        except SurveyValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/survey/template", dependencies=[Depends(verify_api_key)])
def download_blank_survey():
    return FileResponse(TEMPLATES / SURVEY_NAME, filename=SURVEY_NAME)


@app.get("/api/survey/runs/{run_id}", dependencies=[Depends(verify_api_key)])
def survey_run_status(run_id: str):
    try:
        return get_survey_status(run_id, RUNS_DIR)
    except SurveyValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/survey/runs/{run_id}/survey/preview", dependencies=[Depends(verify_api_key)])
def preview_survey(run_id: str):
    from dataclasses import asdict
    from html import escape
    from ecostream.ingestion.survey_workbook import read_survey

    _validate_safe_identifier(run_id, "run_id")
    try:
        metadata = get_survey_status(run_id, RUNS_DIR)
    except SurveyValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    workspace = BlackboardWorkspace(run_id, RUNS_DIR)
    survey = os.path.join(workspace.deliverables_dir, SURVEY_FILE)
    if not os.path.isfile(survey):
        raise HTTPException(status_code=404, detail="Chưa có biểu khảo sát")
    gi = dict(metadata.get("general_info") or {})
    try:
        data = read_survey(survey)
        if data.general_info:
            for key, value in asdict(data.general_info).items():
                if value:
                    gi[key] = value
        rows = "".join(f"<tr><td>{escape(item.sheet)}!{escape(item.coordinate)}</td><td>{escape(item.kind)}</td><td>{item.month}</td><td>{item.quantity:g}</td><td>{escape(item.unit)}</td></tr>" for item in data.items)
    except SurveyValidationError as exc:
        rows = f"<tr><td colspan='5'>{escape(str(exc))}</td></tr>"
    info_lines = [
        ("Người cung cấp thông tin", gi.get("contact_name", "")), ("Chức vụ/Bộ phận", gi.get("contact_role", "")),
        ("Điện thoại (người cung cấp)", gi.get("contact_phone", "")), ("Email (người cung cấp)", gi.get("contact_email", "")),
        ("1. Tên cơ sở", gi.get("facility_name") or metadata.get("facility", "")), ("Địa chỉ", gi.get("facility_address", "")),
        ("Điện thoại cơ sở", gi.get("facility_phone", "")), ("Email cơ sở", gi.get("facility_email", "")),
        ("Người đại diện pháp luật", f"{gi.get('legal_representative', '')}{' — ' + gi.get('legal_rep_title', '') if gi.get('legal_rep_title') else ''}".strip(" —")),
        ("Ngành nghề SX/KD", gi.get("industry_sector", "")),
        ("Tình trạng / Năm bắt đầu", f"{gi.get('operating_status', '')}{' / ' + gi.get('start_year', '') if gi.get('start_year') else ''}".strip(" /")),
        ("Đại diện cơ sở", gi.get("facility_representative", "")),
    ]
    info_rows = "".join(f"<tr><th>{escape(label)}</th><td>{escape(value) if value else '<span>Chưa điền</span>'}</td></tr>" for label, value in info_lines)
    provenance = "".join(f"<li>{escape(str(entry['filename']))}: {escape(str(entry['status']))} — {entry['records']} dòng</li>" for entry in metadata["files"])
    warnings = "".join(f"<li>{escape(str(message))}</li>" for message in metadata["warnings"])
    return HTMLResponse("<!doctype html><html lang='vi'><meta charset='utf-8'><title>Biểu khảo sát</title><style>body{font:15px Arial,sans-serif;margin:1.5rem;color:#0f172a}td,th{border:1px solid #cbd5e1;padding:.45rem .6rem}table{border-collapse:collapse;width:100%;margin-bottom:1.25rem}button{margin:.75rem 0;padding:.45rem .9rem;cursor:pointer}h2{margin:1.25rem 0 .5rem;font-size:1.05rem}@media print{button{display:none}}</style><h1>Biểu khảo sát số liệu hoạt động — bản xem để in</h1><p>Kiểm tra lại thông tin cơ sở, số liệu và nguồn trước khi tính. Bản xem này gồm thông tin chung và dữ liệu Scope 1/2; tải Excel để xem toàn bộ mẫu.</p><button onclick='window.print()'>In trang</button><h2>Thông tin chung của cơ sở</h2><table><tbody>" + info_rows + "</tbody></table><h2>Số liệu hoạt động Scope 1/2</h2><table><thead><tr><th>Ô khảo sát</th><th>Nguồn</th><th>Tháng</th><th>Số lượng</th><th>Đơn vị</th></tr></thead><tbody>" + rows + "</tbody></table><h2>Chứng từ</h2><ul>" + provenance + "</ul><h2>Cần rà soát</h2><ul>" + warnings + "</ul></html>")


class SurveyWorkbookSaveRequest(BaseModel):
    general_info: Optional[dict] = None
    sheet_1_1: Optional[list] = None
    sheet_1_2: Optional[list] = None
    sheet_2_1: Optional[list] = None
    extra_cells: Optional[dict] = None


@app.get("/api/survey/runs/{run_id}/survey/data", dependencies=[Depends(verify_api_key)])
def read_survey_workbook_data(run_id: str):
    _validate_safe_identifier(run_id, "run_id")
    try:
        return get_survey_workbook_data(run_id, RUNS_DIR)
    except SurveyValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/survey/runs/{run_id}/survey/save", dependencies=[Depends(verify_api_key)])
def write_survey_workbook_data(run_id: str, payload: SurveyWorkbookSaveRequest):
    _validate_safe_identifier(run_id, "run_id")
    try:
        return save_survey_workbook_data(run_id, payload.model_dump(exclude_none=True), RUNS_DIR)
    except SurveyValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/survey/runs/{run_id}/calculate", dependencies=[Depends(verify_api_key)])
async def calculate_survey_run(run_id: str, reviewed: Optional[UploadFile] = File(None)):
    _validate_safe_identifier(run_id, "run_id")
    with tempfile.TemporaryDirectory() as temp_dir:
        path = None
        if reviewed is not None:
            if not (reviewed.filename or "").lower().endswith(".xlsx"):
                raise HTTPException(status_code=422, detail="Bản khảo sát đã sửa phải là tệp .xlsx")
            content = await reviewed.read(MAX_SURVEY_FILE_BYTES + 1)
            if len(content) > MAX_SURVEY_FILE_BYTES:
                raise HTTPException(status_code=413, detail="Tệp khảo sát quá 10 MB")
            path = os.path.join(temp_dir, "reviewed.xlsx")
            with open(path, "wb") as stream:
                stream.write(content)
            _validate_uploaded_document(path, "reviewed.xlsx")
        try:
            return calculate_survey(run_id, path, RUNS_DIR)
        except SurveyValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/survey/runs/{run_id}/files/{kind}", dependencies=[Depends(verify_api_key)])
def download_survey_file(run_id: str, kind: str):
    _validate_safe_identifier(run_id, "run_id")
    names = {"survey": SURVEY_FILE, "inventory": INVENTORY_FILE, "report": REPORT_FILE}
    if kind not in names:
        raise HTTPException(status_code=404, detail="Loại tệp không tồn tại")
    try:
        get_survey_status(run_id, RUNS_DIR)
    except SurveyValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    workspace = BlackboardWorkspace(run_id, RUNS_DIR)
    path = os.path.join(workspace.deliverables_dir, names[kind])
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Tệp chưa được tạo")
    return FileResponse(path, filename=names[kind])


@app.get("/api/survey/runs/{run_id}/survey", dependencies=[Depends(verify_api_key)])
def download_generated_survey(run_id: str):
    return download_survey_file(run_id, "survey")


@app.get("/api/orchestrator/runs", include_in_schema=False, dependencies=[Depends(verify_api_key)])
def list_runs(org_id: Optional[str] = Query(None), x_org_id: Optional[str] = Header(None, alias="X-Org-Id")):
    if not os.path.exists(RUNS_DIR):
        return {"runs": []}
    filter_org = org_id or x_org_id
    runs = []
    for name in sorted(os.listdir(RUNS_DIR), reverse=True):
        run_dir = os.path.join(RUNS_DIR, name)
        if not os.path.isdir(run_dir):
            continue
        tenant_meta = _load_tenant_meta(run_dir)
        if filter_org and tenant_meta.get("org_id") not in (filter_org, "public"):
            continue
        workspace = BlackboardWorkspace(name, RUNS_DIR)
        state = workspace.load_state()
        runs.append({"run_id": name, "org_id": tenant_meta.get("org_id", "public"), "user_id": tenant_meta.get("user_id", "anonymous"),
                     "state": state.model_dump() if state else None, "phase": state.phase.value if state else "UNKNOWN",
                     "progress_pct": state.progress_pct if state else 0.0, "start_time": state.start_time if state else None,
                     "end_time": state.end_time if state else None,
                     "queries_count": len(workspace.load_intermediate_json("query_log.json") or []),
                     "assumptions_count": len(workspace.load_intermediate_json("assumption_log.json") or []),
                     "deliverables_count": len(workspace.list_deliverables()), "intermediate_count": len(workspace.list_intermediate_files()),
                     "has_deliverables": bool(workspace.list_deliverables())})
    return {"runs": runs}


@app.get("/api/orchestrator/runs/{run_id}", dependencies=[Depends(verify_api_key)])
def get_run_details(run_id: str):
    _validate_safe_identifier(run_id, "run_id")
    workspace = BlackboardWorkspace(run_id, RUNS_DIR)
    state = workspace.load_state()
    if not state:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    index = workspace.load_index()
    intermediate = {name: workspace.load_intermediate_json(filename) for name, filename in {
        "scope1": "scope1_extracted.json", "scope2": "scope2_extracted.json", "scope3": "scope3_extracted.json",
        "mitigation": "mitigation_extracted.json", "math_results": "math_results.json", "mitigation_summary": "mitigation_summary.json",
        "queries": "query_log.json", "assumptions": "assumption_log.json",
    }.items()}
    return {"run_id": run_id, "state": state.model_dump(), "index": index.model_dump() if index else None,
            "intermediate": {key: (value or []) if key in ("scope1", "scope2", "scope3", "mitigation", "queries", "assumptions") else value for key, value in intermediate.items()},
            "intermediate_files": workspace.list_intermediate_files(), "deliverables": workspace.list_deliverables(),
            "manifest": workspace.get_file_manifest(), "math_results": intermediate["math_results"],
            "mitigation_summary": intermediate["mitigation_summary"], "queries": intermediate["queries"] or [], "assumptions": intermediate["assumptions"] or []}


@app.get("/api/orchestrator/runs/{run_id}/files", dependencies=[Depends(verify_api_key)])
def get_run_files(run_id: str):
    _validate_safe_identifier(run_id, "run_id")
    workspace = BlackboardWorkspace(run_id, RUNS_DIR)
    if not os.path.exists(workspace.run_dir):
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return workspace.get_file_manifest()


@app.get("/api/orchestrator/runs/{run_id}/intermediate/{filename}", dependencies=[Depends(verify_api_key)])
def get_intermediate_file(run_id: str, filename: str):
    _validate_safe_identifier(run_id, "run_id")
    workspace = BlackboardWorkspace(run_id, RUNS_DIR)
    path = _verify_safe_path(workspace.intermediate_dir, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail=f"Intermediate file {filename} not found")
    if filename.endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return FileResponse(path, media_type="text/plain; charset=utf-8", filename=filename)


@app.get("/api/orchestrator/runs/{run_id}/deliverables/{filename}", dependencies=[Depends(verify_api_key)])
def download_deliverable(run_id: str, filename: str):
    _validate_safe_identifier(run_id, "run_id")
    workspace = BlackboardWorkspace(run_id, RUNS_DIR)
    path = _verify_safe_path(workspace.deliverables_dir, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail=f"Deliverable {filename} not found")
    media_type = "application/octet-stream"
    if filename.endswith(".html"):
        media_type = "text/html"
    elif filename.endswith((".md", ".txt")):
        media_type = "text/markdown; charset=utf-8"
    elif filename.endswith(".json"):
        media_type = "application/json"
    elif filename.endswith(".pdf"):
        media_type = "application/pdf"
    elif filename.endswith(".docx"):
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return FileResponse(path, media_type=media_type, filename=filename)


@app.get("/api/factors", dependencies=[Depends(verify_api_key)])
def list_factors():
    return [factor.model_dump() for factor in get_factor_database().get_all_factors()]


def find_available_port(start_port: int = 8000, host: str = "127.0.0.1", max_attempts: int = 20) -> int:
    for port in range(start_port, start_port + max_attempts):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind((host, port))
            return port
        except OSError:
            sock.close()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
MIN_API_KEY_LENGTH = 16


def assert_safe_to_serve(host: str) -> None:
    if host in LOOPBACK_HOSTS:
        return
    problems = []
    api_key = os.environ.get("ECOSTREAM_API_KEY", "")
    if len(api_key) < MIN_API_KEY_LENGTH:
        problems.append(f"ECOSTREAM_API_KEY (tối thiểu {MIN_API_KEY_LENGTH} ký tự)")
    encryption_key = os.environ.get("ECOSTREAM_ENCRYPTION_KEY", "")
    if not encryption_key:
        problems.append("ECOSTREAM_ENCRYPTION_KEY")
    else:
        try:
            Fernet(encryption_key.encode("utf-8"))
        except (ValueError, TypeError):
            problems.append("ECOSTREAM_ENCRYPTION_KEY không hợp lệ; dùng Fernet.generate_key()")
    if problems:
        raise RuntimeError("Từ chối khởi động trên địa chỉ mạng: thiếu cấu hình bảo mật: " + ", ".join(problems))


def run_server(host: Optional[str] = None, port: Optional[int] = None):
    env_port = os.environ.get("PORT")
    env_host = os.environ.get("ECOSTREAM_HOST") or os.environ.get("HOST")
    if env_port:
        actual_host, actual_port = host or env_host or "0.0.0.0", int(env_port)
    else:
        actual_host = host or env_host or "127.0.0.1"
        actual_port = find_available_port(port or 8000, actual_host)
    assert_safe_to_serve(actual_host)
    print(f"\n[EcoStream] Survey web server is live at: http://{actual_host}:{actual_port}\n")
    uvicorn.run(app, host=actual_host, port=actual_port)


if __name__ == "__main__":
    run_server()
