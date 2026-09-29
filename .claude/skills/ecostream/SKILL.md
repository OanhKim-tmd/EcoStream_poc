---
name: ecostream
description: Ingest business documents, run multi-agent carbon accounting, Decree 06/2022 Mẫu 02 mitigation math, and generate Vietnamese regulatory deliverables.
user-invocable: true
disable-model-invocation: false
---

# EcoStream Multi-Agent Carbon Engine

Execute the end-to-end multi-agent pipeline to process business files (Excel, PDF, DOCX, CSV), route them to specialized domain subagents, execute deterministic carbon & mitigation math, and generate official Vietnamese regulatory deliverables.

## Usage
- `/ecostream --demo` : Run benchmark demo on `data/samples/input.xlsx`
- `/ecostream --input <path_to_file_or_dir>` : Run on custom business files/invoices
- `/ecostream --input <path> --company "Company Name" --facility "Plant Name" --year 2026`

## Procedure
1. Parse arguments from the invocation.
2. If `--demo` or no argument is given, run:
   ```bash
   python -m ecostream.cli --demo
   ```
3. If `--input` is provided:
   ```bash
   python -m ecostream.cli $ARGUMENTS
   ```
4. Verify the deliverables created in `runs/<run_id>/deliverables/`:
   - `Bao_cao_kiem_ke_va_giam_nhe_KNK.md`
   - `Bao_cao_kiem_ke_va_giam_nhe_KNK.html`
   - `Bao_cao_Mau02_ND06.docx`
   - `Bao_cao_kiem_ke_va_giam_nhe_KNK.pdf`
   - `final_inventory_summary.json`
5. Present the summary table, Mẫu 02 mitigation results, and query/assumption logs.
