"""FastAPI web service serving the EcoStream Interactive Carbon & Reliability Dashboard."""

import os
import sys
import shutil
import tempfile
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
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ecostream.ingestion.loaders import DocumentIngestionLoader, IngestedDocument
from ecostream.extraction.extractor import ExtractionEngine
from ecostream.factors.database import get_factor_database
from ecostream.engine.calculator import CarbonCalculator
from ecostream.engine.reliability import ReliabilityEngine
from ecostream.engine.advisor import CarbonAdvisor
from ecostream.models.results import AuditReport
from ecostream.reporting.export import ReportExporter

app = FastAPI(
    title="EcoStream AI Carbon Engine",
    description="Interactive carbon footprint calculation, provenance auditing, and data reliability engine for SMEs.",
    version="0.1.0",
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
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
SAMPLES_DIR = os.path.join(os.path.dirname(BASE_DIR), "data", "samples")

# Cache latest generated report
_latest_report: Optional[AuditReport] = None


def execute_pipeline(
    documents: List[IngestedDocument],
    company_name: str = "EcoGarment Vietnam JSC",
    facility_location: str = "Nam Thang Long IP, Hanoi, Vietnam",
    reporting_period: str = "Tháng 03/2026",
    industry_sector: str = "Garment & Textile Manufacturing",
) -> AuditReport:
    global _latest_report

    extractor = ExtractionEngine()
    records = extractor.extract_batch(documents)

    calc_engine = CarbonCalculator(get_factor_database())
    calculations = calc_engine.calculate_all(records)
    scopes, total_tonnes, total_min, total_max = calc_engine.aggregate_scopes(calculations)

    reliability = ReliabilityEngine.evaluate(records)

    summary = CarbonAdvisor.compile_summary(
        company_name=company_name,
        facility_location=facility_location,
        reporting_period=reporting_period,
        industry_sector=industry_sector,
        records=records,
        calculations=calculations,
        scopes=scopes,
        total_tonnes=total_tonnes,
        total_min=total_min,
        total_max=total_max,
        reliability=reliability,
    )

    report = AuditReport(
        report_id=f"ECO-RPT-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        summary=summary,
        calculations=calculations,
    )
    _latest_report = report
    return report


@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h2>EcoStream Dashboard UI is being loaded...</h2>")


@app.get("/api/demo")
def run_demo():
    """Run benchmark case study with bundled sample Vietnamese SME documents."""
    docs = DocumentIngestionLoader.load_directory(SAMPLES_DIR)
    if not docs:
        raise HTTPException(status_code=404, detail="Sample files not found.")
    report = execute_pipeline(docs)
    return report.model_dump()


@app.post("/api/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    company: str = Form("EcoGarment Vietnam JSC"),
    period: str = Form("Tháng 03/2026"),
    location: str = Form("Hanoi, Vietnam"),
):
    """Upload custom business files (text invoices, CSV manifests, Excel) for processing."""
    documents: List[IngestedDocument] = []
    with tempfile.TemporaryDirectory() as tmpdir:
        for f in files:
            safe_filename = os.path.basename(f.filename or "uploaded_doc")
            tmp_path = os.path.join(tmpdir, safe_filename)
            content_bytes = await f.read()
            with open(tmp_path, "wb") as buf:
                buf.write(content_bytes)

            doc = DocumentIngestionLoader.load_file(tmp_path)
            doc.filename = safe_filename
            doc.metadata["uploaded_at"] = datetime.now().isoformat()
            documents.append(doc)

    report = execute_pipeline(
        documents=documents,
        company_name=company,
        reporting_period=period,
        facility_location=location,
    )
    return report.model_dump()


@app.get("/api/report/html", response_class=HTMLResponse)
def get_report_html():
    """Export the most recent calculation as printable standalone HTML."""
    global _latest_report
    if not _latest_report:
        run_demo()
    return HTMLResponse(ReportExporter.to_html(_latest_report))


@app.get("/api/report/markdown", response_class=PlainTextResponse)
def get_report_markdown():
    """Export the most recent calculation as Markdown."""
    global _latest_report
    if not _latest_report:
        run_demo()
    return PlainTextResponse(ReportExporter.to_markdown(_latest_report))


@app.get("/api/report/pdf")
def get_report_pdf():
    """Export the most recent calculation as an audit-ready standalone vector PDF."""
    global _latest_report
    if not _latest_report:
        run_demo()
    from fastapi.responses import Response
    pdf_bytes = ReportExporter.to_pdf(_latest_report)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=EcoStream_Carbon_Audit_Report.pdf"},
    )


@app.get("/api/factors")
def list_factors():
    """List all registered emission factors with uncertainty and source reference."""
    db = get_factor_database()
    return [f.model_dump() for f in db._factors.values()]


def find_available_port(preferred_port: int, host: str = "127.0.0.1") -> int:
    import socket
    ports_to_try = [preferred_port, 8080, 8501, 8888, 5000, 3000]
    # Deduplicate while preserving order
    candidate_ports = []
    for p in ports_to_try:
        if p not in candidate_ports:
            candidate_ports.append(p)

    for port in candidate_ports:
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


def run_server(host: str = "127.0.0.1", port: int = 8080):
    actual_port = find_available_port(port, host)
    print(f"\n[EcoStream] Web Server is live at: http://{host}:{actual_port}\n")
    uvicorn.run(app, host=host, port=actual_port)


if __name__ == "__main__":
    run_server()
