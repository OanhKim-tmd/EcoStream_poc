"""FastAPI web service serving the EcoStream Interactive Carbon & Reliability Dashboard with Multi-Agent Orchestrator."""

import os
import sys
import shutil
import tempfile
import socket
from datetime import datetime
from typing import List, Optional

# Configure UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import uvicorn
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Locate base directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
SAMPLES_DIR = os.path.join(PROJECT_ROOT, "data", "samples")
RUNS_DIR = os.path.join(PROJECT_ROOT, "runs")

# Cache latest generated report
_latest_report: Optional[AuditReport] = None

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




@app.get("/api/demo")
def run_demo():
    """Run benchmark case study using multi-agent workflow on data/samples/input.xlsx."""
    global _latest_report
    sample_xlsx = os.path.join(SAMPLES_DIR, "input.xlsx")
    if not os.path.exists(sample_xlsx):
        from scripts.generate_mock_excel import generate_benchmark_excel
        generate_benchmark_excel(sample_xlsx)

    import re
        safe_c = re.sub(r'[^a-zA-Z0-9À-ỹ]+', '-', company).strip('-')
        safe_l = re.sub(r'[^a-zA-Z0-9À-ỹ]+', '-', location).strip('-')
        from datetime import datetime
        ts_suffix = datetime.now().strftime("%H%M%S")
        run_name = f"{safe_c}_{safe_l}_{period}_{ts_suffix}"
        orch = WorkflowOrchestrator(run_id=run_name, offline_mode=True)
    res = orch.run_pipeline(
        input_files=[sample_xlsx],
        company_name="EcoGarment Vietnam JSC",
        facility_name="Nhà máy May & Năng lượng Hà Nam",
        reporting_year=2026,
    )

    # Build backward-compatible AuditReport structure
    deliv_json = os.path.join(orch.workspace.deliverables_dir, "final_inventory_summary.json")
    if os.path.exists(deliv_json):
        with open(deliv_json, "r", encoding="utf-8") as f:
            import json
            report_data = json.load(f)
            _latest_report = AuditReport(**report_data)
            return report_data

    return res


@app.post("/api/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    company: str = Form("EcoGarment Vietnam JSC"),
    period: str = Form("2026"),
    location: str = Form("Nhà máy May & Năng lượng Hà Nam"),
):
    """Upload custom business files (Excel, PDF, Word, CSV) and run multi-agent pipeline."""
    global _latest_report
    temp_dir = tempfile.mkdtemp()
    saved_paths = []
    try:
        for f in files:
            dest_path = os.path.join(temp_dir, f.filename)
            with open(dest_path, "wb") as out_f:
                content = await f.read()
                out_f.write(content)
            saved_paths.append(dest_path)

        # Parse year if available
        year_num = 2026
        try:
            import re
            m = re.search(r"\b(202\d)\b", period)
            if m:
                year_num = int(m.group(1))
        except Exception:
            pass

        import re
        safe_c = re.sub(r'[^a-zA-Z0-9À-ỹ]+', '-', company).strip('-')
        safe_l = re.sub(r'[^a-zA-Z0-9À-ỹ]+', '-', location).strip('-')
        from datetime import datetime
        ts_suffix = datetime.now().strftime("%H%M%S")
        run_name = f"{safe_c}_{safe_l}_{period}_{ts_suffix}"
        orch = WorkflowOrchestrator(run_id=run_name, offline_mode=True)
        res = orch.run_pipeline(
            input_files=saved_paths,
            company_name=company,
            facility_name=location,
            reporting_year=year_num,
        )

        deliv_json = os.path.join(orch.workspace.deliverables_dir, "final_inventory_summary.json")
        if os.path.exists(deliv_json):
            with open(deliv_json, "r", encoding="utf-8") as f:
                import json
                report_data = json.load(f)
                _latest_report = AuditReport(**report_data)
                return report_data

        return res
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        return {"error": "Pipeline Crashed", "details": err_msg}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.get("/api/orchestrator/runs")
def list_runs():
    """List all pipeline execution runs in blackboard workspace."""
    if not os.path.exists(RUNS_DIR):
        return {"runs": []}
    runs = []
    for r_name in sorted(os.listdir(RUNS_DIR), reverse=True):
        r_dir = os.path.join(RUNS_DIR, r_name)
        if os.path.isdir(r_dir):
            workspace = BlackboardWorkspace(r_name, RUNS_DIR)
            state = workspace.load_state()
            queries = workspace.load_intermediate_json("query_log.json") or []
            assumptions = workspace.load_intermediate_json("assumption_log.json") or []
            deliverables = workspace.list_deliverables()
            intermediate_files = workspace.list_intermediate_files()

            runs.append({
                "run_id": r_name,
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


@app.get("/api/orchestrator/runs/{run_id}")
def get_run_details(run_id: str):
    """Get state, index, intermediate extractions, logs, and deliverables for a specific run."""
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


@app.get("/api/orchestrator/runs/{run_id}/files")
def get_run_files(run_id: str):
    """Get directory tree manifest for a specific run."""
    workspace = BlackboardWorkspace(run_id, RUNS_DIR)
    if not os.path.exists(workspace.run_dir):
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found.")
    return workspace.get_file_manifest()


@app.get("/api/orchestrator/runs/{run_id}/intermediate/{filename}")
def get_intermediate_file(run_id: str, filename: str):
    """Fetch raw intermediate JSON/text file."""
    workspace = BlackboardWorkspace(run_id, RUNS_DIR)
    fpath = os.path.join(workspace.intermediate_dir, filename)
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail=f"Intermediate file {filename} not found in run {run_id}.")

    if filename.endswith(".json"):
        with open(fpath, "r", encoding="utf-8") as f:
            import json
            return json.load(f)
    return FileResponse(fpath, media_type="text/plain; charset=utf-8", filename=filename)



@app.get("/api/orchestrator/runs/{run_id}/deliverables/{filename}")
def download_deliverable(run_id: str, filename: str):
    """Download a generated deliverable file (.md, .html, .docx, .pdf, .json)."""
    workspace = BlackboardWorkspace(run_id, RUNS_DIR)
    fpath = os.path.join(workspace.deliverables_dir, filename)
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








@app.get("/api/export/pdf")
@app.get("/api/report/pdf")
def export_pdf():
    global _latest_report
    if not _latest_report:
        run_demo()
    pdf_bytes = ReportExporter.to_pdf(_latest_report)
    return Response(content=pdf_bytes, media_type="application/pdf")


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


def run_server(host: str = "127.0.0.1", port: int = 8000):
    actual_port = find_available_port(port, host)
    print(f"\n[EcoStream] Multi-Agent Web Server is live at: http://{host}:{actual_port}\n")
    uvicorn.run(app, host=host, port=actual_port)


if __name__ == "__main__":
    run_server()
