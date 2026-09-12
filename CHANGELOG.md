# Changelog

All notable changes to the **EcoStream** platform are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] - 2026-09-12

### 🚀 Added
- **Universal Ingestion Layer with Microsoft MarkItDown**:
  - Implemented `MarkItDownNormalizer` in `ecostream/ingestion/markitdown_normalizer.py` to seamlessly convert multi-format documents (digital PDF, Word `.docx`, Excel `.xlsx`, PowerPoint `.pptx`, and text) into GitHub-Flavored Markdown (GFM).
- **OCR Add-on & Scanned Document Support**:
  - Integrated `pytesseract` and `pdf2image` with dual language support (`vie+eng`) for local, private OCR processing of scanned bills and receipts.
  - Added Vision LLM fallback (Gemini Vision) for low-light or degraded receipt scans when configured.
  - Implemented semantic page delimiter injection (`<!-- page: N -->`) to track exact page coordinates in multi-page PDFs.
- **Markdown Pipe Table Parser**:
  - Added `MarkdownTableParser` in `ecostream/extraction/parsers.py` to extract road freight transport (`ton-km`), purchased packaging/materials (`kg`), and spend proxies (`VND`) from MarkItDown-generated GFM tables.
  - Full provenance tracking linking every calculation back to `Table Row X` or `Page N, Line L`.
- **Multi-Format Binary Upload API**:
  - Updated `POST /api/upload` in `ecostream/app/server.py` to store uploaded binary files in temporary directories, preventing UTF-8 decoding corruption for PDF, Excel, and image uploads.
- **Advisor Data Quality Feedback**:
  - Added `REC-OCR-UPGRADE` recommendation in `CarbonAdvisor` to guide SMEs on transitioning from scanned receipts to certified digital invoices (XML/PDF) for Grade A audit readiness.
- **Automated Test Suite**:
  - Added `tests/test_markitdown_normalizer.py` covering fast-path ingestion, table parsing, document loader integration, and multipart API uploads (17/17 tests passing).

### 🛠 Changed
- Updated `DocumentIngestionLoader` in `ecostream/ingestion/loaders.py` to delegate multi-format parsing to `MarkItDownNormalizer`.
- Updated Web UI upload card in `ecostream/app/static/index.html` to display support for `.pdf, .xlsx, .docx, .png, .jpg, .txt, .csv, .log`.
- Updated `requirements.txt` with `markitdown`, `pytesseract`, `pdf2image`, `python-docx`, `openpyxl`, and `Pillow`.
- Fixed ReportLab PDF export font fallback on Linux environments (`LiberationSans` / `DejaVuSans` / `Helvetica`).

---

## [0.1.0] - 2026-09-12

### 🚀 Initial Release
- **5-Stage Pipeline Architecture**:
  - Stage 1: Ingestion Layer (`ecostream/ingestion/loaders.py`).
  - Stage 2: Extraction & Evidence Layer (`ecostream/extraction/extractor.py`, `parsers.py`).
  - Stage 3: Quality & Reliability Engine (`ecostream/engine/reliability.py`).
  - Stage 4: Carbon Engine & Uncertainty Propagation (`ecostream/engine/calculator.py`).
  - Stage 5: Decision & Roadmap Advisor (`ecostream/engine/advisor.py`).
- **GHG Protocol Scope 1, 2, 3 Accounting**:
  - Vietnam-specific emission factors (MONRE grid factor 0.7221 kg CO2/kWh, Petrolimex fuels, logistics, packaging).
  - Statistical error propagation with 95% Confidence Interval.
- **5-Dimensional Data Reliability Scoring**:
  - Radar assessment (Completeness, Temporal, Geographical Fit, Source Reliability, Extraction Confidence) with Grade A to D classification.
- **Audit-Ready Reporting**:
  - Standalone HTML, Markdown, and PDF export with full evidence lineage table.
- **Interactive Web Dashboard & CLI**:
  - FastAPI server with Chart.js visualization (`ecostream.app`).
  - Command-line runner (`ecostream.cli --demo`).
