"""Command-line interface for EcoStream Multi-Agent Carbon Data Engine."""

import argparse
import os
import sys
from datetime import datetime

# Configure UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ecostream.orchestrator.pipeline import WorkflowOrchestrator
from ecostream.factors.database import get_factor_database

console = Console(force_terminal=True, legacy_windows=False)


def run_multiagent_pipeline(
    input_paths: list[str],
    company_name: str = "EcoGarment Vietnam JSC",
    facility_name: str = "Nhà máy May & Năng lượng Hà Nam",
    reporting_year: int = 2026,
    run_id: str = None,
) -> dict:
    console.print(
        Panel.fit(
            f"[bold green]EcoStream Multi-Agent AI Carbon Engine[/bold green]\n"
            f"[cyan]Target Enterprise:[/cyan] {company_name}\n"
            f"[cyan]Facility / Location:[/cyan] {facility_name}\n"
            f"[cyan]Reporting Year:[/cyan] {reporting_year} | [cyan]Input Files:[/cyan] {len(input_paths)} files",
            title="EcoStream Orchestrator Workflow",
            border_style="green",
        )
    )

    orchestrator = WorkflowOrchestrator(run_id=run_id)
    console.print(f"[bold yellow]Executing multi-agent pipeline (Run ID: {orchestrator.run_id})...[/bold yellow]\n")

    result = orchestrator.run_pipeline(
        input_files=input_paths,
        company_name=company_name,
        facility_name=facility_name,
        reporting_year=reporting_year,
    )

    summary = result["summary"]
    rel = summary["reliability"]

    # 1. Scope Breakdown Table
    table = Table(title="Tổng Hợp Phát Thải Khí Nhà Kính (Corporate GHG Inventory)")
    table.add_column("Phạm vi (Scope)", style="cyan", justify="left")
    table.add_column("Phát thải (tCO₂e)", justify="right", style="bold")
    table.add_column("Tỷ trọng (%)", justify="right")
    table.add_column("Khoảng tin cậy 95%", justify="center")
    table.add_column("Độ tin cậy", justify="center", style="green")

    for s in summary["scopes"]:
        table.add_row(
            s["scope"],
            f"{s['total_tonnes']:,.3f}",
            f"{s['percentage']:.1f}%",
            f"[{s['uncertainty_lower_tonnes']:.2f} - {s['uncertainty_upper_tonnes']:.2f}] t",
            f"{s['avg_confidence_pct']:.1f}%",
        )
    table.add_section()
    table.add_row(
        "[bold]Tổng Phát Thải Ròng[/bold]",
        f"[bold]{summary['total_co2e_tonnes']:,.3f}[/bold]",
        "100.0%",
        f"[bold][{summary['total_uncertainty_min_tonnes']:.2f} - {summary['total_uncertainty_max_tonnes']:.2f}] t[/bold]",
        f"[bold]{rel['overall_confidence_score']:.1f}% (Grade {rel['grade']})[/bold]",
    )
    console.print(table)

    # 2. Mitigation Table (Mau 02 ND 06/2022) - HIDDEN for EcoStream POC Stage 1
    # if result.get("mitigation_summary"):
    #     ...
    #         console.print(f"[cyan]Hạn ngạch phân bổ:[/cyan] {qp['allocated_quota_tonnes']:,.1f} tCO₂e | [cyan]Phát thải sau giảm nhẹ:[/cyan] {qp['net_compliance_emissions_tonnes']:,.1f} tCO₂e | [bold yellow]{qp['compliance_status']}[/bold yellow]\n")

    # 3. Query & Assumption Logs Table
    if result.get("queries") or result.get("assumptions"):
        q_table = Table(title="Dấu Vết Kiểm Toán (Audit Trail: Query Log & Assumption Log)")
        q_table.add_column("Mã Log", style="cyan", justify="left")
        q_table.add_column("Loại bất thường / Tham số", justify="left")
        q_table.add_column("Hành động xử lý tự động / Giả định áp dụng", justify="left")
        q_table.add_column("Phạt tin cậy", justify="right", style="red")

        for q in result.get("queries", []):
            q_table.add_row(
                f"[bold]{q['query_id']}[/bold]",
                f"{q['field_name']} ({q['anomaly_type']})",
                q["action_taken"][:65] + "...",
                "-",
            )
        for a in result.get("assumptions", []):
            q_table.add_row(
                f"[bold]{a['assumption_id']}[/bold]",
                f"{a['parameter_name']} = {a['assumed_value']} {a['assumed_unit']}",
                a["justification"][:65] + "...",
                f"-{a['confidence_penalty']*100:.1f}%",
            )
        console.print(q_table)

    # Deliverables Panel
    deliv = result.get("deliverables", {})
    deliv_msg = (
        f"[green]✔ Deliverables saved in blackboard workspace:[/green]\n"
        f"  • JSON Summary: [cyan]{deliv.get('json')}[/cyan]\n"
        f"  • Excel Workbook (QA & Hồ sơ CO2): [cyan]{deliv.get('excel')}[/cyan]\n"
        f"  • Markdown Report: [cyan]{deliv.get('markdown')}[/cyan]\n"
        f"  • Standalone HTML: [cyan]{deliv.get('html')}[/cyan]\n"
        f"  • Word Document: [cyan]{deliv.get('docx')}[/cyan]\n"
        f"  • PDF Report: [cyan]{deliv.get('pdf')}[/cyan]\n"
        f"  • Run Workspace: [italic]{deliv.get('run_dir')}[/italic]"
    )
    console.print(Panel.fit(deliv_msg, title="Export Complete", border_style="cyan"))
    return result


def main():
    parser = argparse.ArgumentParser(description="EcoStream Multi-Agent Carbon Engine CLI")
    parser.add_argument("--input", nargs="+", help="Input file(s) or folder (e.g. data/samples/input.xlsx)")
    parser.add_argument("--demo", action="store_true", help="Run with default benchmark input dataset")
    parser.add_argument("--company", default="EcoGarment Vietnam JSC", help="Company Name")
    parser.add_argument("--facility", default="Nhà máy May & Năng lượng Hà Nam", help="Facility Name")
    parser.add_argument("--year", type=int, default=2026, help="Reporting Year")
    parser.add_argument("--run-id", default=None, help="Custom Run ID")

    args = parser.parse_args()

    input_files = []
    if args.input:
        for p in args.input:
            if os.path.isdir(p):
                for f in sorted(os.listdir(p)):
                    input_files.append(os.path.join(p, f))
            elif os.path.isfile(p):
                input_files.append(p)
    elif args.demo or not args.input:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sample_xlsx = os.path.join(base_dir, "data", "samples", "input.xlsx")
        if not os.path.exists(sample_xlsx):
            from scripts.generate_mock_excel import generate_benchmark_excel
            generate_benchmark_excel(sample_xlsx)
        input_files = [sample_xlsx]

    run_multiagent_pipeline(
        input_paths=input_files,
        company_name=args.company,
        facility_name=args.facility,
        reporting_year=args.year,
        run_id=args.run_id,
    )


if __name__ == "__main__":
    main()
