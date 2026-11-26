"""Command-line interface for the survey workflow (chứng từ → biểu khảo sát → Scope 1/2 → kết quả).

Usage:
  python -m ecostream.cli --demo
  python -m ecostream.cli --input <file_or_dir> [...] --company "Tên" --facility "Nhà máy" --year 2026
  python -m ecostream.cli --run-id <run_id> --reviewed <Bang_khao_sat.xlsx>

Biểu khảo sát được tạo tự động từ chứng từ. Trước khi nộp, cần rà soát lại
biểu (sheet 1.x, 2.x) và tính lại bằng --run-id ... --reviewed ...
"""

import argparse
import os
import sys
from pathlib import Path

from ecostream.orchestrator.survey_pipeline import (
    prepare_survey, calculate_survey, SURVEY_FILE, INVENTORY_FILE, REPORT_FILE,
)
from ecostream.ingestion.survey_workbook import SurveyValidationError

ROOT = Path(__file__).resolve().parents[1]
DEMO_INPUT = ROOT / "data" / "samples" / "input.xlsx"


def _collect_inputs(paths: list[str]) -> list[str]:
    files: list[str] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            files.extend(str(f) for f in sorted(p.iterdir()) if f.is_file() and not f.name.startswith("~$"))
        elif p.is_file():
            files.append(str(p))
        else:
            raise SurveyValidationError(f"Không tìm thấy tệp hoặc thư mục: {raw}")
    if not files:
        raise SurveyValidationError("Không có chứng từ nào để xử lý")
    return files


def _print_result(outcome: dict, run_id: str, runs_dir: str | None) -> None:
    summary = outcome["summary"]
    base = Path(runs_dir) if runs_dir else Path(os.environ.get("ECOSTREAM_RUNS_DIR", ROOT / "runs"))
    deliv = base / run_id / "deliverables"
    print(f"\nMã phiên: {run_id}")
    print(f"Năm báo cáo: {summary.get('reporting_period')}")
    print(f"Scope 1: {summary['scope_1_tonnes']:.3f} tCO2e")
    print(f"Scope 2: {summary['scope_2_tonnes']:.3f} tCO2e")
    print(f"Scope 3: {summary['scope_3_tonnes']:.3f} tCO2e (ngoài phạm vi luồng khảo sát)")
    print(f"Tổng:    {summary['total_co2e_tonnes']:.3f} tCO2e")
    print(f"Độ tin cậy: {summary['reliability']['grade']} ({summary['reliability']['overall_confidence_score']})")
    if outcome.get("warnings"):
        print("\nCảnh báo:")
        for w in outcome["warnings"]:
            print(f"  - {w}")
    print("\nTệp kết quả:")
    for name in (SURVEY_FILE, INVENTORY_FILE, REPORT_FILE):
        print(f"  {deliv / name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ecostream", description="EcoStream: kiểm kê KNK cấp cơ sở (Scope 1/2)")
    parser.add_argument("--demo", action="store_true", help="Chạy dữ liệu mẫu data/samples/input.xlsx")
    parser.add_argument("--input", nargs="+", metavar="PATH", help="Tệp hoặc thư mục chứng từ")
    parser.add_argument("--company", default="Cơ sở kiểm kê", help="Tên doanh nghiệp")
    parser.add_argument("--facility", default="Nhà máy", help="Tên cơ sở")
    parser.add_argument("--year", type=int, default=2026, help="Năm báo cáo")
    parser.add_argument("--run-id", dest="run_id", help="Tính lại một phiên đã có")
    parser.add_argument("--reviewed", help="Biểu khảo sát đã rà soát (dùng với --run-id)")
    parser.add_argument("--runs-dir", help="Thư mục lưu phiên (mặc định: runs/ hoặc ECOSTREAM_RUNS_DIR)")
    args = parser.parse_args(argv)

    modes = sum(bool(x) for x in (args.demo, args.input, args.run_id))
    if modes != 1:
        parser.error("Chọn đúng một trong: --demo, --input, --run-id")

    try:
        if args.run_id:
            outcome = calculate_survey(args.run_id, reviewed_file=args.reviewed, base_runs_dir=args.runs_dir)
            _print_result(outcome, args.run_id, args.runs_dir)
            return 0

        files = [str(DEMO_INPUT)] if args.demo else _collect_inputs(args.input)
        company, facility = (("Cơ sở kiểm thử", "Nhà máy A") if args.demo else (args.company, args.facility))
        year = 2026 if args.demo else args.year
        prep = prepare_survey(files, company, facility, year, args.runs_dir)
        print("Đã tạo biểu khảo sát từ chứng từ.")
        if prep.get("warnings"):
            print("Cảnh báo khi trích xuất:")
            for w in prep["warnings"]:
                print(f"  - {w}")
        outcome = calculate_survey(prep["run_id"], base_runs_dir=args.runs_dir)
        _print_result(outcome, prep["run_id"], args.runs_dir)
        return 0
    except SurveyValidationError as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
