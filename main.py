"""
I2M Research Agent — Tavily API POC
=====================================
Tests Tavily's real-time search for business market research,
using LangGraph's Send() to run 6 sub-tasks in parallel:
  1. Market Sizing        (TAM / SAM / SOM)
  2. Competitor Matrix    (3–5 competitors)
  3. Risk Analysis        (top regulatory & adoption risks)
  4. Tech & Marketing     (recommended stack + GTM strategy)
  5. USP Analysis         (competitor USPs + how to differentiate)
  6. Build Timeline       (phase-by-phase estimate to launch)

Usage:
  python main.py   ← prompts for idea interactively
"""

import os
import re
import sys
from datetime import datetime

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

load_dotenv()

# Validate required env vars early
_REQUIRED = [
    "TAVILY_API_KEY",
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
]
_missing = [k for k in _REQUIRED if not os.environ.get(k)]
if _missing:
    print(f"[ERROR] Missing environment variables: {', '.join(_missing)}")
    print("Copy .env.example → .env and fill in your keys.")
    sys.exit(1)

# Import after env check so Azure/Tavily clients initialise cleanly
from src.graph import research_graph  # noqa: E402

console = Console()


# ---------------------------------------------------------------------------
# Pretty-print helpers
# ---------------------------------------------------------------------------

def _print_market(data: dict):
    table = Table(title="Market Sizing", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_row("TAM", data.get("tam", "—"))
    table.add_row("SAM", data.get("sam", "—"))
    table.add_row("SOM", data.get("som", "—"))
    table.add_row("Growth Rate", data.get("growth_rate", "—"))
    console.print(table)
    if data.get("market_summary"):
        console.print(Panel(data["market_summary"], title="Market Summary", border_style="cyan"))


def _print_competitors(data: dict):
    table = Table(title="Competitor Matrix", show_header=True, header_style="bold magenta")
    table.add_column("Name", style="bold")
    table.add_column("Description")
    table.add_column("Pricing")
    table.add_column("Strengths")
    table.add_column("Weaknesses")
    for c in data.get("competitors", []):
        table.add_row(
            c.get("name", "—"),
            c.get("description", "—"),
            c.get("pricing", "—"),
            "\n".join(f"• {s}" for s in c.get("strengths", [])),
            "\n".join(f"• {w}" for w in c.get("weaknesses", [])),
        )
    console.print(table)


def _print_risks(data: dict):
    severity_color = {"high": "red", "medium": "yellow", "low": "green"}
    table = Table(title="Risk Analysis", show_header=True, header_style="bold red")
    table.add_column("Risk", style="bold")
    table.add_column("Category")
    table.add_column("Severity")
    table.add_column("Mitigation")
    for r in data.get("risks", []):
        sev = r.get("severity", "medium").lower()
        color = severity_color.get(sev, "white")
        table.add_row(
            r.get("risk", "—"),
            r.get("category", "—"),
            Text(sev.upper(), style=f"bold {color}"),
            r.get("mitigation", "—"),
        )
    console.print(table)


def _print_tech_marketing_strategy(data: dict):
    tech = data.get("technical_strategy", {})
    mkt = data.get("marketing_strategy", {})

    tech_table = Table(title="Technical Strategy", show_header=True, header_style="bold blue")
    tech_table.add_column("Aspect", style="bold")
    tech_table.add_column("Details")
    tech_table.add_row("Recommended Stack", "\n".join(f"• {s}" for s in tech.get("recommended_stack", [])))
    tech_table.add_row("Architecture", tech.get("architecture", "—"))
    tech_table.add_row("Key Integrations", "\n".join(f"• {i}" for i in tech.get("key_integrations", [])))
    tech_table.add_row("Build Approach", tech.get("build_approach", "—"))
    console.print(tech_table)

    mkt_table = Table(title="Marketing Strategy", show_header=True, header_style="bold yellow")
    mkt_table.add_column("Aspect", style="bold")
    mkt_table.add_column("Details")
    mkt_table.add_row("Primary Channels", "\n".join(f"• {c}" for c in mkt.get("primary_channels", [])))
    mkt_table.add_row("Target Segments", "\n".join(f"• {s}" for s in mkt.get("target_segments", [])))
    mkt_table.add_row("Key Tactics", "\n".join(f"• {t}" for t in mkt.get("key_tactics", [])))
    console.print(mkt_table)
    if mkt.get("gtm_approach"):
        console.print(Panel(mkt["gtm_approach"], title="GTM Approach", border_style="yellow"))


def _print_usp_analysis(data: dict):
    usp_table = Table(title="Competitor USPs", show_header=True, header_style="bold magenta")
    usp_table.add_column("Competitor", style="bold")
    usp_table.add_column("Their USP")
    for item in data.get("competitor_usps", []):
        usp_table.add_row(item.get("competitor", "—"), item.get("usp", "—"))
    console.print(usp_table)

    diff_table = Table(title="How Your Product Should Be Unique", show_header=True, header_style="bold green")
    diff_table.add_column("#", style="bold", width=3)
    diff_table.add_column("Differentiator")
    for i, d in enumerate(data.get("recommended_differentiators", []), 1):
        diff_table.add_row(str(i), d)
    console.print(diff_table)

    if data.get("positioning_statement"):
        console.print(Panel(data["positioning_statement"], title="Positioning Statement", border_style="green"))


def _print_build_timeline(data: dict):
    table = Table(title="Estimated Build Timeline", show_header=True, header_style="bold cyan")
    table.add_column("Phase", style="bold")
    table.add_column("Duration")
    table.add_column("Key Deliverables")
    for phase in data.get("phases", []):
        table.add_row(
            phase.get("phase", "—"),
            phase.get("duration", "—"),
            "\n".join(f"• {d}" for d in phase.get("key_deliverables", [])),
        )
    console.print(table)

    summary_lines = []
    if data.get("total_estimate"):
        summary_lines.append(f"**Total Estimate:** {data['total_estimate']}")
    if data.get("team_size_assumption"):
        summary_lines.append(f"**Team:** {data['team_size_assumption']}")
    if data.get("complexity_factors"):
        factors = " · ".join(data["complexity_factors"])
        summary_lines.append(f"**Complexity Factors:** {factors}")
    if summary_lines:
        console.print(Panel("\n".join(summary_lines), title="Build Summary", border_style="cyan"))


def _print_sources(sources: list):
    if not sources:
        return
    console.print("\n[bold]Sources[/bold]")
    for i, url in enumerate(sources[:10], 1):
        console.print(f"  [{i}] {url}")


# ---------------------------------------------------------------------------
# Markdown report builder
# ---------------------------------------------------------------------------

def _build_markdown(idea: str, output: dict) -> str:
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines.append(f"# Research Report: {idea}")
    lines.append(f"\n> Generated by I2M Research Agent · {now}\n")

    # Executive Summary
    if output.get("executive_summary"):
        lines.append("## Executive Summary\n")
        lines.append(output["executive_summary"])
        lines.append("")

    # Market Sizing
    lines.append("## Market Sizing\n")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| TAM | {output.get('tam', '—')} |")
    lines.append(f"| SAM | {output.get('sam', '—')} |")
    lines.append(f"| SOM | {output.get('som', '—')} |")
    lines.append(f"| Growth Rate | {output.get('growth_rate', '—')} |")
    if output.get("market_summary"):
        lines.append(f"\n{output['market_summary']}")
    lines.append("")

    # Competitor Matrix
    lines.append("## Competitor Matrix\n")
    lines.append("| Company | Description | Pricing | Strengths | Weaknesses |")
    lines.append("|---------|-------------|---------|-----------|------------|")
    for c in output.get("competitors", []):
        strengths = " · ".join(c.get("strengths", []))
        weaknesses = " · ".join(c.get("weaknesses", []))
        lines.append(
            f"| **{c.get('name', '—')}** | {c.get('description', '—')} "
            f"| {c.get('pricing', '—')} | {strengths} | {weaknesses} |"
        )
    lines.append("")

    # Risk Analysis
    lines.append("## Risk Analysis\n")
    lines.append("| Risk | Category | Severity | Mitigation |")
    lines.append("|------|----------|----------|------------|")
    severity_badge = {"high": "🔴 HIGH", "medium": "🟡 MEDIUM", "low": "🟢 LOW"}
    for r in output.get("risks", []):
        sev = r.get("severity", "medium").lower()
        badge = severity_badge.get(sev, sev.upper())
        lines.append(
            f"| {r.get('risk', '—')} | {r.get('category', '—')} "
            f"| {badge} | {r.get('mitigation', '—')} |"
        )
    lines.append("")

    # Technical Strategy
    tech = output.get("technical_strategy", {})
    mkt = output.get("marketing_strategy", {})
    if tech or mkt:
        lines.append("## Technical & Marketing Strategy\n")
        if tech:
            lines.append("### Technical Strategy\n")
            lines.append("| Aspect | Details |")
            lines.append("|--------|---------|")
            stack = " · ".join(tech.get("recommended_stack", []))
            lines.append(f"| Recommended Stack | {stack} |")
            lines.append(f"| Architecture | {tech.get('architecture', '—')} |")
            integrations = " · ".join(tech.get("key_integrations", []))
            lines.append(f"| Key Integrations | {integrations} |")
            lines.append(f"| Build Approach | {tech.get('build_approach', '—')} |")
            lines.append("")
        if mkt:
            lines.append("### Marketing Strategy\n")
            lines.append("| Aspect | Details |")
            lines.append("|--------|---------|")
            channels = " · ".join(mkt.get("primary_channels", []))
            lines.append(f"| Primary Channels | {channels} |")
            segments = " · ".join(mkt.get("target_segments", []))
            lines.append(f"| Target Segments | {segments} |")
            tactics = " · ".join(mkt.get("key_tactics", []))
            lines.append(f"| Key Tactics | {tactics} |")
            if mkt.get("gtm_approach"):
                lines.append(f"\n**GTM Approach:** {mkt['gtm_approach']}")
            lines.append("")

    # USP Analysis
    competitor_usps = output.get("competitor_usps", [])
    differentiators = output.get("recommended_differentiators", [])
    positioning = output.get("positioning_statement", "")
    if competitor_usps or differentiators:
        lines.append("## USP Analysis\n")
        if competitor_usps:
            lines.append("### Competitor USPs\n")
            lines.append("| Competitor | Their USP |")
            lines.append("|------------|-----------|")
            for item in competitor_usps:
                lines.append(f"| **{item.get('competitor', '—')}** | {item.get('usp', '—')} |")
            lines.append("")
        if differentiators:
            lines.append("### How Your Product Should Be Unique\n")
            for d in differentiators:
                lines.append(f"- {d}")
            lines.append("")
        if positioning:
            lines.append(f"> **Positioning Statement:** {positioning}\n")

    # Build Timeline
    build_phases = output.get("build_phases", [])
    total_estimate = output.get("total_estimate", "")
    team_assumption = output.get("team_size_assumption", "")
    complexity_factors = output.get("complexity_factors", [])
    if build_phases or total_estimate:
        lines.append("## Estimated Build Timeline\n")
        if build_phases:
            lines.append("| Phase | Duration | Key Deliverables |")
            lines.append("|-------|----------|-----------------|")
            for phase in build_phases:
                deliverables = " · ".join(phase.get("key_deliverables", []))
                lines.append(
                    f"| **{phase.get('phase', '—')}** | {phase.get('duration', '—')} | {deliverables} |"
                )
            lines.append("")
        if total_estimate:
            lines.append(f"**Total Estimate:** {total_estimate}  ")
        if team_assumption:
            lines.append(f"**Team:** {team_assumption}  ")
        if complexity_factors:
            lines.append(f"**Complexity Factors:** {' · '.join(complexity_factors)}")
        lines.append("")

    # Sources
    sources = output.get("sources", [])
    if sources:
        lines.append("## Sources\n")
        for i, url in enumerate(sources[:15], 1):
            lines.append(f"{i}. {url}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(idea: str):
    console.rule("[bold blue]I2M Research Agent — Tavily POC")
    console.print(Panel(f"[bold]{idea}[/bold]", title="Business Idea", border_style="blue"))
    console.print("\n[dim]Running 6 parallel Tavily searches (market · competitors · risks · strategy · USP · timeline)...[/dim]\n")

    # Stream graph execution so we can see each node as it completes
    final_state = None
    for event in research_graph.stream(
        {"idea": idea, "research_results": []},
        stream_mode="values",
    ):
        node_name = list(event.keys())[-1] if event else ""
        if node_name not in ("research_output",):
            # Show a simple progress indicator per completed node
            results = event.get("research_results", [])
            if results:
                last = results[-1]
                console.print(f"  [green]✓[/green] {last['type'].replace('_', ' ').title()} complete")
        final_state = event

    output = final_state.get("research_output") if final_state else None
    if not output:
        console.print("[red]No research output produced. Check your API keys and try again.[/red]")
        return

    console.rule("[bold green]Research Complete")

    # Executive summary
    if output.get("executive_summary"):
        console.print(Panel(output["executive_summary"], title="Executive Summary", border_style="green"))

    # Individual sections
    _print_market(output)
    _print_competitors(output)
    _print_risks(output)
    _print_tech_marketing_strategy(output)
    _print_usp_analysis(output)
    _print_build_timeline(output)
    _print_sources(output.get("sources", []))

    # Save as Markdown in outputs/
    os.makedirs("outputs", exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "_", idea.lower()).strip("_")[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join("outputs", f"{slug}_{timestamp}.md")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(_build_markdown(idea, output))

    console.print(f"\n[dim]Report saved → {output_path}[/dim]")


if __name__ == "__main__":
    idea_input = console.input("[bold]Enter your business idea:[/bold] ").strip()

    if not idea_input:
        console.print("[red]No idea provided. Exiting.[/red]")
        sys.exit(1)

    run(idea_input)
