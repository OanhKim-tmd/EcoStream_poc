"""Command-line interface for EcoStream Carbon Data Engine."""

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

from ecostream.ingestion.loaders import DocumentIngestionLoader
from ecostream.extraction.extractor import ExtractionEngine
from ecostream.factors.database import get_factor_database
from ecostream.engine.calculator import CarbonCalculator
from ecostream.engine.reliability import ReliabilityEngine
from ecostream.engine.advisor import CarbonAdvisor
from ecostream.models.results import AuditReport
from ecostream.reporting.export import ReportExporter

console = Console(force_terminal=True, legacy_windows=False)


def run_pipeline(
    data_dir: str,
    company_name: str = "EcoGarment Vietnam JSC",
    facility_location: str = "Nam Thang Long IP, Hanoi, Vietnam",
    reporting_period: str = "Tháng 03/2026",
    industry: str = "Garment & Textile Manufacturing",
    export_dir: str = ".",
) -> AuditReport:
    console.print(
        Panel.fit(
            f"[bold green]EcoStream AI Carbon Engine[/bold green]\n"
            f"[cyan]Target Enterprise:[/cyan] {company_name}\n"
            f"[cyan]Period:[/cyan] {reporting_period} | [cyan]Location:[/cyan] {facility_location}",
            title="EcoStream PoC Pipeline",
            border_style="green",
        )
    )

    # 1. Ingestion
    console.print("\n[bold yellow]Step 1: Document Ingestion[/bold yellow]")
    docs = DocumentIngestionLoader.load_directory(data_dir)
    console.print(f"Loaded [bold cyan]{len(docs)}[/bold cyan] business files from [italic]{data_dir}[/italic]")
    for d in docs:
        console.print(f"  • [blue]{d.filename}[/blue] ({d.file_type}) - {len(d.content)} chars")

    # 2. Extraction & Evidence Layer
    console.print("\n[bold yellow]Step 2: AI & Rule-Based Extraction (Evidence Layer)[/bold yellow]")
    extractor = ExtractionEngine()
    records = extractor.extract_batch(docs)
    console.print(f"Extracted [bold cyan]{len(records)}[/bold cyan] structured activity records with source provenance.")

    # 3. Calculation & Scope Categorization
    console.print("\n[bold yellow]Step 3: GHG Calculation & Uncertainty Propagation[/bold yellow]")
    calc_engine = CarbonCalculator(get_factor_database())
    calculations = calc_engine.calculate_all(records)
    scopes, total_tonnes, total_min, total_max = calc_engine.aggregate_scopes(calculations)

    # 4. Reliability & Confidence Scoring
    console.print("\n[bold yellow]Step 4: 5-Dimensional Reliability Assessment[/bold yellow]")
    reliability = ReliabilityEngine.evaluate(records)

    # 5. Advisor & Roadmap
    console.print("\n[bold yellow]Step 5: Decision Support & Hotspot Analysis[/bold yellow]")
    summary = CarbonAdvisor.compile_summary(
        company_name=company_name,
        facility_location=facility_location,
        reporting_period=reporting_period,
        industry_sector=industry,
        records=records,
        calculations=calculations,
        scopes=scopes,
        total_tonnes=total_tonnes,
        total_min=total_min,
        total_max=total_max,
        reliability=reliability,
    )

    report = AuditReport(
        report_id=f"ECO-RPT-{datetime.now().strftime('%Y%m%d-%H%M')}",
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        summary=summary,
        calculations=calculations,
    )

    # Display Scope Summary Table
    table = Table(title="GHG Emissions by Scope (GHG Protocol)")
    table.add_column("Scope", style="cyan", justify="left")
    table.add_column("Emissions (tCO2e)", justify="right", style="bold")
    table.add_column("Share (%)", justify="right")
    table.add_column("95% Uncertainty Interval", justify="center")
    table.add_column("Avg Confidence", justify="center", style="green")

    for s in scopes:
        table.add_row(
            s.scope.value,
            f"{s.total_tonnes:.3f}",
            f"{s.percentage:.1f}%",
            f"[{s.uncertainty_lower_tonnes:.2f} - {s.uncertainty_upper_tonnes:.2f}] t",
            f"{s.avg_confidence_pct:.1f}%",
        )
    table.add_section()
    table.add_row(
        "[bold]Grand Total[/bold]",
        f"[bold]{total_tonnes:.3f}[/bold]",
        "100.0%",
        f"[bold][{total_min:.2f} - {total_max:.2f}] t[/bold]",
        f"[bold]{reliability.overall_confidence_score:.1f}% (Grade {reliability.grade})[/bold]",
    )
    console.print(table)

    # Reliability Dimensions Table
    dim_table = Table(title="EcoStream 5-Dimension Confidence Radar")
    dim_table.add_column("Dimension", style="cyan")
    dim_table.add_column("Score", justify="right", style="bold")
    dim_table.add_column("Grade", justify="center")
    dim_table.add_column("Notes", style="dim")

    for k, d in reliability.dimensions.items():
        dim_table.add_row(d.name, f"{d.score:.1f}%", f"Grade {d.grade}", d.explanation)
    console.print(dim_table)

    # Export Reports
    md_path = os.path.join(export_dir, "report_audit.md")
    html_path = os.path.join(export_dir, "report_audit.html")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(ReportExporter.to_markdown(report))

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(ReportExporter.to_html(report))

    console.print(f"\n[bold green]✔ Audit Reports successfully exported:[/bold green]")
    console.print(f"  • Markdown: [cyan]{os.path.abspath(md_path)}[/cyan]")
    console.print(f"  • HTML:     [cyan]{os.path.abspath(html_path)}[/cyan]")

    return report


def main():
    parser = argparse.ArgumentParser(description="EcoStream AI Carbon Engine CLI")
    parser.add_argument("--demo", action="store_true", help="Run benchmark demo with sample SME dataset")
    parser.add_argument("--data-dir", default=None, help="Directory containing invoices, receipts, and spreadsheets")
    parser.add_argument("--company", default="EcoGarment Vietnam JSC", help="Company Name")
    parser.add_argument("--output", default=".", help="Output directory for reports")

    args = parser.parse_args()

    data_dir = args.data_dir
    if args.demo or not data_dir:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(base_dir, "data", "samples")

    if not os.path.exists(data_dir):
        console.print(f"[red]Error: Data directory '{data_dir}' not found.[/red]")
        sys.exit(1)

    run_pipeline(
        data_dir=data_dir,
        company_name=args.company,
        export_dir=args.output,
    )


if __name__ == "__main__":
    main()
