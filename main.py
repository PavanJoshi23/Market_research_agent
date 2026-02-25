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

_REQUIRED = [
    "SEARXNG_HOST",
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
]
_missing = [k for k in _REQUIRED if not os.environ.get(k)]
if _missing:
    print(f"[ERROR] Missing environment variables: {', '.join(_missing)}")
    sys.exit(1)

from langgraph.types import Command  # noqa: E402

from src.graph import research_graph  # noqa: E402

console = Console()


def _print_market(data: dict):
    table = Table(title="Market Sizing", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_row("TAM", data.get("tam", "-"))
    table.add_row("SAM", data.get("sam", "-"))
    table.add_row("SOM", data.get("som", "-"))
    table.add_row("Growth Rate", data.get("growth_rate", "-"))
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
            c.get("name", "-"),
            c.get("description", "-"),
            c.get("pricing", "-"),
            "\n".join(f"- {s}" for s in c.get("strengths", [])),
            "\n".join(f"- {w}" for w in c.get("weaknesses", [])),
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
        table.add_row(
            r.get("risk", "-"),
            r.get("category", "-"),
            Text(sev.upper(), style=f"bold {severity_color.get(sev, 'white')}"),
            r.get("mitigation", "-"),
        )
    console.print(table)


def _print_tech_marketing_strategy(data: dict):
    tech = data.get("technical_strategy", {})
    mkt = data.get("marketing_strategy", {})

    tech_table = Table(title="Technical Strategy", show_header=True, header_style="bold blue")
    tech_table.add_column("Aspect", style="bold")
    tech_table.add_column("Details")
    tech_table.add_row("Recommended Stack", "\n".join(f"- {s}" for s in tech.get("recommended_stack", [])))
    tech_table.add_row("Architecture", tech.get("architecture", "-"))
    tech_table.add_row("Key Integrations", "\n".join(f"- {i}" for i in tech.get("key_integrations", [])))
    tech_table.add_row("Build Approach", tech.get("build_approach", "-"))
    console.print(tech_table)

    mkt_table = Table(title="Marketing Strategy", show_header=True, header_style="bold yellow")
    mkt_table.add_column("Aspect", style="bold")
    mkt_table.add_column("Details")
    mkt_table.add_row("Primary Channels", "\n".join(f"- {c}" for c in mkt.get("primary_channels", [])))
    mkt_table.add_row("Target Segments", "\n".join(f"- {s}" for s in mkt.get("target_segments", [])))
    mkt_table.add_row("Key Tactics", "\n".join(f"- {t}" for t in mkt.get("key_tactics", [])))
    console.print(mkt_table)
    if mkt.get("gtm_approach"):
        console.print(Panel(mkt["gtm_approach"], title="GTM Approach", border_style="yellow"))


def _print_usp_analysis(data: dict):
    usp_table = Table(title="Competitor USPs", show_header=True, header_style="bold magenta")
    usp_table.add_column("Competitor", style="bold")
    usp_table.add_column("Their USP")
    for item in data.get("competitor_usps", []):
        usp_table.add_row(item.get("competitor", "-"), item.get("usp", "-"))
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
    for phase in data.get("build_phases", data.get("phases", [])):
        table.add_row(
            phase.get("phase", "-"),
            phase.get("duration", "-"),
            "\n".join(f"- {d}" for d in phase.get("key_deliverables", [])),
        )
    console.print(table)

    summary_lines = []
    if data.get("total_estimate"):
        summary_lines.append(f"**Total Estimate:** {data['total_estimate']}")
    if data.get("team_size_assumption"):
        summary_lines.append(f"**Team:** {data['team_size_assumption']}")
    if data.get("complexity_factors"):
        summary_lines.append(f"**Complexity Factors:** {' - '.join(data['complexity_factors'])}")
    if summary_lines:
        console.print(Panel("\n".join(summary_lines), title="Build Summary", border_style="cyan"))


def _print_sources(sources: list):
    if not sources:
        return
    console.print("\n[bold]Sources[/bold]")
    for i, url in enumerate(sources[:10], 1):
        console.print(f"  [{i}] {url}")


def _print_tldr_questions(tldr: str, questions: list[str]):
    console.rule("[bold yellow]Turn 1 Complete — Clarification Needed")
    console.print(Panel(tldr, title="TLDR", border_style="yellow"))
    console.print("\n[bold]Questions about your idea:[/bold]")
    for i, q in enumerate(questions, 1):
        console.print(f"  {i}. {q}")
    console.print()


def _print_output(output: dict):
    if output.get("executive_summary"):
        console.print(Panel(output["executive_summary"], title="Executive Summary", border_style="green"))
    _print_market(output)
    _print_competitors(output)
    _print_risks(output)
    _print_tech_marketing_strategy(output)
    _print_usp_analysis(output)
    _print_build_timeline(output)
    _print_sources(output.get("sources", []))


def _build_markdown(idea: str, output: dict) -> str:
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines.append(f"# Research Report: {idea}")
    lines.append(f"\n> Generated by I2M Research Agent - {now}\n")

    if output.get("executive_summary"):
        lines.append("## Executive Summary\n")
        lines.append(output["executive_summary"])
        lines.append("")

    lines.append("## Market Sizing\n")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| TAM | {output.get('tam', '-')} |")
    lines.append(f"| SAM | {output.get('sam', '-')} |")
    lines.append(f"| SOM | {output.get('som', '-')} |")
    lines.append(f"| Growth Rate | {output.get('growth_rate', '-')} |")
    if output.get("market_summary"):
        lines.append(f"\n{output['market_summary']}")
    lines.append("")

    lines.append("## Competitor Matrix\n")
    lines.append("| Company | Description | Pricing | Strengths | Weaknesses |")
    lines.append("|---------|-------------|---------|-----------|------------|")
    for c in output.get("competitors", []):
        strengths = " - ".join(c.get("strengths", []))
        weaknesses = " - ".join(c.get("weaknesses", []))
        lines.append(
            f"| **{c.get('name', '-')}** | {c.get('description', '-')} "
            f"| {c.get('pricing', '-')} | {strengths} | {weaknesses} |"
        )
    lines.append("")

    lines.append("## Risk Analysis\n")
    lines.append("| Risk | Category | Severity | Mitigation |")
    lines.append("|------|----------|----------|------------|")
    for r in output.get("risks", []):
        sev = r.get("severity", "medium").upper()
        lines.append(
            f"| {r.get('risk', '-')} | {r.get('category', '-')} "
            f"| {sev} | {r.get('mitigation', '-')} |"
        )
    lines.append("")

    tech = output.get("technical_strategy", {})
    mkt = output.get("marketing_strategy", {})
    if tech or mkt:
        lines.append("## Technical & Marketing Strategy\n")
        if tech:
            lines.append("### Technical Strategy\n")
            lines.append("| Aspect | Details |")
            lines.append("|--------|---------|")
            lines.append(f"| Recommended Stack | {' - '.join(tech.get('recommended_stack', []))} |")
            lines.append(f"| Architecture | {tech.get('architecture', '-')} |")
            lines.append(f"| Key Integrations | {' - '.join(tech.get('key_integrations', []))} |")
            lines.append(f"| Build Approach | {tech.get('build_approach', '-')} |")
            lines.append("")
        if mkt:
            lines.append("### Marketing Strategy\n")
            lines.append("| Aspect | Details |")
            lines.append("|--------|---------|")
            lines.append(f"| Primary Channels | {' - '.join(mkt.get('primary_channels', []))} |")
            lines.append(f"| Target Segments | {' - '.join(mkt.get('target_segments', []))} |")
            lines.append(f"| Key Tactics | {' - '.join(mkt.get('key_tactics', []))} |")
            if mkt.get("gtm_approach"):
                lines.append(f"\n**GTM Approach:** {mkt['gtm_approach']}")
            lines.append("")

    competitor_usps = output.get("competitor_usps", [])
    differentiators = output.get("recommended_differentiators", [])
    if competitor_usps or differentiators:
        lines.append("## USP Analysis\n")
        if competitor_usps:
            lines.append("### Competitor USPs\n")
            lines.append("| Competitor | Their USP |")
            lines.append("|------------|-----------|")
            for item in competitor_usps:
                lines.append(f"| **{item.get('competitor', '-')}** | {item.get('usp', '-')} |")
            lines.append("")
        if differentiators:
            lines.append("### How Your Product Should Be Unique\n")
            for d in differentiators:
                lines.append(f"- {d}")
            lines.append("")
        if output.get("positioning_statement"):
            lines.append(f"> **Positioning Statement:** {output['positioning_statement']}\n")

    build_phases = output.get("build_phases", output.get("phases", []))
    if build_phases or output.get("total_estimate"):
        lines.append("## Estimated Build Timeline\n")
        if build_phases:
            lines.append("| Phase | Duration | Key Deliverables |")
            lines.append("|-------|----------|-----------------|")
            for phase in build_phases:
                deliverables = " - ".join(phase.get("key_deliverables", []))
                lines.append(
                    f"| **{phase.get('phase', '-')}** | {phase.get('duration', '-')} | {deliverables} |"
                )
            lines.append("")
        if output.get("total_estimate"):
            lines.append(f"**Total Estimate:** {output['total_estimate']}  ")
        if output.get("team_size_assumption"):
            lines.append(f"**Team:** {output['team_size_assumption']}  ")
        if output.get("complexity_factors"):
            lines.append(f"**Complexity Factors:** {' - '.join(output['complexity_factors'])}")
        lines.append("")

    sources = output.get("sources", [])
    if sources:
        lines.append("## Sources\n")
        for i, url in enumerate(sources[:15], 1):
            lines.append(f"{i}. {url}")
        lines.append("")

    return "\n".join(lines)


def _save_report(idea: str, output: dict):
    os.makedirs("outputs", exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "_", idea.lower()).strip("_")[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join("outputs", f"{slug}_{timestamp}.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(_build_markdown(idea, output))
    console.print(f"\n[dim]Report saved -> {output_path}[/dim]")


def run(idea: str):
    console.rule("[bold blue]I2M Research Agent")
    console.print(Panel(f"[bold]{idea}[/bold]", title="Business Idea", border_style="blue"))
    console.print("\n[dim]Running 6 parallel searches (market - competitors - risks - strategy - USP - timeline)...[/dim]\n")

    config = {"configurable": {"thread_id": "1"}}
    interrupt_data = None

    for event in research_graph.stream(
        {"idea": idea, "research_results": []},
        config=config,
        stream_mode="updates",
    ):
        if "__interrupt__" in event:
            interrupt_data = event["__interrupt__"][0].value
            break

        for node_name, node_state in event.items():
            results = node_state.get("research_results", [])
            if results:
                last = results[-1]
                console.print(f"  [green]v[/green] {last['type'].replace('_', ' ').title()} complete")

    if not interrupt_data:
        console.print("[red]No research output produced. Check your API keys and try again.[/red]")
        return

    tldr = interrupt_data.get("tldr", "")
    questions = interrupt_data.get("questions", [])
    _print_tldr_questions(tldr, questions)

    console.print("[bold]Please answer the questions above (press Enter twice when done):[/bold]")
    answer_lines = []
    while True:
        line = input()
        if line == "" and answer_lines and answer_lines[-1] == "":
            break
        answer_lines.append(line)
    answers = "\n".join(answer_lines).strip()

    console.print("\n[dim]Running targeted follow-up research...[/dim]\n")

    final_state = None
    for event in research_graph.stream(
        Command(resume=answers),
        config=config,
        stream_mode="updates",
    ):
        for node_name, node_state in event.items():
            if node_name == "followup_research":
                results = node_state.get("followup_results", [])
                for r in results:
                    console.print(f"  [green]v[/green] {r['type'].replace('_', ' ').title()} (Turn 2) complete")
        final_state = event

    snapshot = research_graph.get_state(config)
    output = snapshot.values.get("research_output")

    if not output:
        console.print("[red]No final output produced.[/red]")
        return

    console.rule("[bold green]Research Complete (Turn 2)")
    _print_output(output)
    _save_report(idea, output)


if __name__ == "__main__":
    idea_input = console.input("[bold]Enter your business idea:[/bold] ").strip()
    if not idea_input:
        console.print("[red]No idea provided. Exiting.[/red]")
        sys.exit(1)
    run(idea_input)
