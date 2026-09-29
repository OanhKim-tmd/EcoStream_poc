# Changelog — EcoStream

All notable changes to the EcoStream AI Carbon Accounting & Reliability Engine are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] - 2026-09-29

### 🚀 Major Architectural Refactoring: AI Multi-Agent, Blackboard Orchestrator & Live Monitor

#### Added
- **Multi-Agent Blackboard Architecture (`ecostream/orchestrator/`)**:
  - Isolated run workspaces under `runs/<run_id>/` managing `state.json`, `index.json`, intermediate extractions (`intermediate/*.json`), dual logs, and deliverables.
  - Lifecycle state machine supporting 5 phases: `INGESTION` $\to$ `DISCOVERY` $\to$ `EXTRACTION` $\to$ `MATH_AND_MITIGATION` $\to$ `SYNTHESIS` $\to$ `COMPLETED`.
- **Microsoft MarkItDown Universal Ingestion & OCR (`ecostream/ingestion/`)**:
  - `markitdown_loader.py` & `markitdown_normalizer.py`: Seamlessly converts multi-tab Excel (`.xlsx`), PDF, Word (`.docx`), PowerPoint, and CSV files into modular Markdown inputs (`input_<SheetName>.md`).
  - Integrated `pytesseract` and `pdf2image` with dual language support (`vie+eng`) for local OCR processing of scanned bills.
  - `cache.py`: SHA-256 fingerprint caching avoiding re-processing unmodified documents.
- **Specialized Domain Subagents (`ecostream/agents/` & `.claude/agents/`)**:
  - `ag-discovery`: Schema discovery, sheet cataloging, and task routing in `index.json`.
  - `ag-scope1-fuel`: Stationary & mobile fuel combustion extraction (diesel, gasoline, coal, LPG packaging conversions).
  - `ag-scope2-power`: EVN utility grid power invoice extraction with seasonal linear interpolation for missing billing months.
  - `ag-scope3-supply`: Freight logistics (tonne-km) and spend-based procurement proxy extraction.
  - `ag-mitigation-quota`: Decree 06/2022/NĐ-CP & Decree 119/2025/NĐ-CP Mẫu 02 facility mitigation and quota surplus/deficit accounting.
  - `ag-synthesizer`: Official Vietnamese regulatory GHG disclosure and executive roadmap generation.
- **Non-blocking Dual-Logging Engine (`runs/<run_id>/intermediate/`)**:
  - `query_log.json`: Logs anomalies, missing billing periods, and low-confidence proxy usages for human auditor verification.
  - `assumption_log.json`: Documents conservative IPCC/TCVN estimation assumptions and records data reliability confidence score deductions.
- **Decree 06/2022/NĐ-CP Mẫu 02 Mitigation Math Engine (`ecostream/engine/mitigation_math.py`)**:
  - Exact facility emission reduction calculations ($GPT = PT_{CS} - PT$).
  - Emission quota surplus/deficit tracking ($Quota_{\text{alloc}} - PT$).
  - Word (`.docx`) table export adhering strictly to Phụ lục IV Mẫu 02.
- **Dedicated Live Workflow Monitoring Dashboard (`ecostream/app/static/monitor.html` & `monitor.js`)**:
  - Standalone pure HTML/JavaScript monitoring interface at `/monitor`.
  - Configurable real-time polling engine (default 3s) with Play/Pause controls and countdown timer.
  - Run selector dropdown and path input to inspect any historical or active run in `runs/`.
  - 5-Phase Lifecycle Stepper visualizer showing current progress, timestamp, and duration.
  - Tabbed Intermediate JSON Inspector for Scope 1, Scope 2, Scope 3, Mẫu 02, Query Log, Assumption Log, Index, and State.
  - Deliverables panel with one-click download for Markdown, HTML, DOCX, PDF, and JSON.
- **Claude Code Native Subagents, Skills & Workflow (`.claude/`)**:
  - Defined subagent configurations in `.claude/agents/*.md` configured with `model: agy/gemini-3.7-flash-low`.
  - Skills for interactive execution: `/ecostream`, `/mitigation`, `/audit`.
  - Dynamic multi-agent workflow script in `.claude/workflows/wf-ecostream.js`.
- **Deliverable Templates & Multi-format Exporters (`ecostream/reporting/`)**:
  - `Bao_cao_kiem_ke_va_giam_nhe_KNK.md`
  - `Bao_cao_kiem_ke_va_giam_nhe_KNK.html`
  - `Bao_cao_Mau02_ND06.docx`
  - `Bao_cao_kiem_ke_va_giam_nhe_KNK.pdf`
  - `final_inventory_summary.json`
- **Expanded Automated Test Suite (35 Unit & Integration Tests)**:
  - `test_markitdown_ingestion.py`: Universal ingestion and SHA-256 caching tests.
  - `test_mitigation_math.py`: Mẫu 02 mitigation math and quota tests.
  - `test_monitor_api.py`: Monitor endpoints and intermediate JSON retrieval tests.
  - `test_orchestrator_e2e.py`: Full end-to-end multi-agent pipeline tests.
  - `test_query_assumption_logs.py`: Data imputation, anomaly logging, and confidence penalty tests.
  - `test_subagents.py`: Domain subagent isolation tests.

#### Changed
- `ecostream/app/server.py`: Added `/monitor`, `/api/orchestrator/runs`, `/api/orchestrator/runs/{run_id}`, `/api/orchestrator/runs/{run_id}/files`, and `/api/orchestrator/runs/{run_id}/intermediate/{filename}` endpoints.
- `ecostream/cli.py`: Updated CLI to support multi-agent pipeline arguments (`--input`, `--company`, `--facility`, `--year`, `--demo`).
- `ecostream/engine/reliability.py`: Enhanced 5-dimensional scoring model to penalize spend proxies and apply deductions from assumption logs.
- `ecostream/factors/database.py`: Added helper lookup methods (`get_all_factors()`, `list_factors()`) for API and subagent consumption.
- `tests/test_pipeline.py`: Realigned benchmark tests with the new multi-agent inventory baseline ($4,945.05\text{ tCO}_2\text{e}$).

---

## [0.1.0] - 2026-09-12

### Initial Release: EcoStream Proof of Concept
- Core 5-dimensional data reliability engine (`Completeness`, `Temporal`, `Geographical`, `Source`, `Extraction`).
- Scope 1, Scope 2, Scope 3 deterministic calculator with Gaussian 95% Confidence Interval error propagation.
- Basic regex-based document parsers for EVN bills, Petrolimex invoices, freight logistics CSVs, and supplier spend tables.
- Interactive Web Dashboard (`FastAPI` + `Chart.js` + `Bootstrap 5`).
- Initial Vietnamese and English reporting exporters (`Markdown`, `HTML`, `PDF`).
