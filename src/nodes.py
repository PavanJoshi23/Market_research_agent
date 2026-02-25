"""
LangGraph node functions for the Research Agent.

Nodes:
  intake              — validates and normalises the idea input
  market_sizing       — Tavily search → LLM extraction of TAM/SAM/SOM
  competitor_matrix   — Tavily search → LLM extraction of competitor list
  risk_analysis       — Tavily search → LLM extraction of top risks
  merge_research      — LLM synthesis of all three results into ResearchOutput
"""

import json
import os
import re

from langchain.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI

from .prompts import (
    BUILD_TIMELINE_PROMPT,
    COMPETITOR_MATRIX_PROMPT,
    MARKET_SIZING_PROMPT,
    MERGE_PROMPT,
    RISK_ANALYSIS_PROMPT,
    TECH_MARKETING_STRATEGY_PROMPT,
    USP_ANALYSIS_PROMPT,
)
from .state import ResearchState
from .tools import competitor_tool, market_tool, risk_tool, strategy_tool

# ---------------------------------------------------------------------------
# LLM — Azure OpenAI
# ---------------------------------------------------------------------------

llm = AzureChatOpenAI(
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
    openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    temperature=1,
    streaming=False,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_search_results(results: list[dict]) -> str:
    """Convert Tavily result list into a compact text block for the LLM."""
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r.get('title', 'No title')}")
        lines.append(f"    URL: {r.get('url', '')}")
        lines.append(f"    {r.get('content', '')}")
        lines.append("")
    return "\n".join(lines)


def _extract_sources(results: list[dict]) -> list[str]:
    return [r.get("url", "") for r in results if r.get("url")]


def _parse_json_response(content: str) -> dict:
    """Strip markdown fences if present and parse JSON."""
    content = content.strip()

    # Extract content between ```...``` fences (handles ```json, trailing newlines, etc.)
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
    if fence_match:
        content = fence_match.group(1).strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Fallback: find the outermost {...} block in case there's surrounding prose
        brace_match = re.search(r"\{.*\}", content, re.DOTALL)
        if brace_match:
            return json.loads(brace_match.group(0))
        raise


# ---------------------------------------------------------------------------
# intake
# ---------------------------------------------------------------------------

def intake(state: ResearchState) -> dict:
    idea = state["idea"].strip()
    if not idea:
        raise ValueError("Idea cannot be empty.")
    return {"idea": idea, "research_results": []}


# ---------------------------------------------------------------------------
# market_sizing
# ---------------------------------------------------------------------------

def market_sizing(state: ResearchState) -> dict:
    idea = state["idea"]

    # Two targeted Tavily queries for market data
    q1 = market_tool.invoke(f"{idea} market size TAM SAM SOM billion")
    q2 = market_tool.invoke(f"{idea} industry revenue forecast growth rate")

    all_results = (q1 if isinstance(q1, list) else q1.get("results", [])) + \
                  (q2 if isinstance(q2, list) else q2.get("results", []))

    sources = _extract_sources(all_results)
    context = _format_search_results(all_results)

    messages = [
        SystemMessage(content=MARKET_SIZING_PROMPT),
        HumanMessage(content=f"Business idea: {idea}\n\nSearch results:\n{context}"),
    ]
    response = llm.invoke(messages)
    data = _parse_json_response(response.content)
    data["sources"] = list(set(sources + data.get("sources", [])))

    return {
        "research_results": [{"type": "market_sizing", "data": data}]
    }


# ---------------------------------------------------------------------------
# competitor_matrix
# ---------------------------------------------------------------------------

def competitor_matrix(state: ResearchState) -> dict:
    idea = state["idea"]

    q1 = competitor_tool.invoke(f"{idea} top competitors alternatives comparison")
    q2 = competitor_tool.invoke(f"{idea} competing startups pricing plans")

    all_results = (q1 if isinstance(q1, list) else q1.get("results", [])) + \
                  (q2 if isinstance(q2, list) else q2.get("results", []))

    sources = _extract_sources(all_results)
    context = _format_search_results(all_results)

    messages = [
        SystemMessage(content=COMPETITOR_MATRIX_PROMPT),
        HumanMessage(content=f"Business idea: {idea}\n\nSearch results:\n{context}"),
    ]
    response = llm.invoke(messages)
    data = _parse_json_response(response.content)
    data["sources"] = list(set(sources + data.get("sources", [])))

    return {
        "research_results": [{"type": "competitor_matrix", "data": data}]
    }


# ---------------------------------------------------------------------------
# risk_analysis
# ---------------------------------------------------------------------------

def risk_analysis(state: ResearchState) -> dict:
    idea = state["idea"]

    q1 = risk_tool.invoke(f"{idea} regulatory risks legal challenges 2024 2025")
    q2 = risk_tool.invoke(f"{idea} market adoption barriers customer concerns")

    all_results = (q1 if isinstance(q1, list) else q1.get("results", [])) + \
                  (q2 if isinstance(q2, list) else q2.get("results", []))

    sources = _extract_sources(all_results)
    context = _format_search_results(all_results)

    messages = [
        SystemMessage(content=RISK_ANALYSIS_PROMPT),
        HumanMessage(content=f"Business idea: {idea}\n\nSearch results:\n{context}"),
    ]
    response = llm.invoke(messages)
    data = _parse_json_response(response.content)
    data["sources"] = list(set(sources + data.get("sources", [])))

    return {
        "research_results": [{"type": "risk_analysis", "data": data}]
    }


# ---------------------------------------------------------------------------
# tech_marketing_strategy
# ---------------------------------------------------------------------------

def tech_marketing_strategy(state: ResearchState) -> dict:
    idea = state["idea"]

    q1 = strategy_tool.invoke(f"{idea} technology stack architecture best practices build")
    q2 = strategy_tool.invoke(f"{idea} go-to-market strategy marketing channels customer acquisition")

    all_results = (q1 if isinstance(q1, list) else q1.get("results", [])) + \
                  (q2 if isinstance(q2, list) else q2.get("results", []))

    sources = _extract_sources(all_results)
    context = _format_search_results(all_results)

    messages = [
        SystemMessage(content=TECH_MARKETING_STRATEGY_PROMPT),
        HumanMessage(content=f"Business idea: {idea}\n\nSearch results:\n{context}"),
    ]
    response = llm.invoke(messages)
    data = _parse_json_response(response.content)
    data["sources"] = list(set(sources + data.get("sources", [])))

    return {
        "research_results": [{"type": "tech_marketing_strategy", "data": data}]
    }


# ---------------------------------------------------------------------------
# usp_analysis
# ---------------------------------------------------------------------------

def usp_analysis(state: ResearchState) -> dict:
    idea = state["idea"]

    q1 = competitor_tool.invoke(f"{idea} unique value proposition USP product differentiation")
    q2 = competitor_tool.invoke(f"{idea} what makes it unique features comparison gap in market")

    all_results = (q1 if isinstance(q1, list) else q1.get("results", [])) + \
                  (q2 if isinstance(q2, list) else q2.get("results", []))

    sources = _extract_sources(all_results)
    context = _format_search_results(all_results)

    messages = [
        SystemMessage(content=USP_ANALYSIS_PROMPT),
        HumanMessage(content=f"Business idea: {idea}\n\nSearch results:\n{context}"),
    ]
    response = llm.invoke(messages)
    data = _parse_json_response(response.content)
    data["sources"] = list(set(sources + data.get("sources", [])))

    return {
        "research_results": [{"type": "usp_analysis", "data": data}]
    }


# ---------------------------------------------------------------------------
# build_timeline
# ---------------------------------------------------------------------------

def build_timeline(state: ResearchState) -> dict:
    idea = state["idea"]

    q1 = strategy_tool.invoke(f"{idea} MVP development timeline how long to build")
    q2 = strategy_tool.invoke(f"{idea} startup engineering team size cost to build product")

    all_results = (q1 if isinstance(q1, list) else q1.get("results", [])) + \
                  (q2 if isinstance(q2, list) else q2.get("results", []))

    sources = _extract_sources(all_results)
    context = _format_search_results(all_results)

    messages = [
        SystemMessage(content=BUILD_TIMELINE_PROMPT),
        HumanMessage(content=f"Business idea: {idea}\n\nSearch results:\n{context}"),
    ]
    response = llm.invoke(messages)
    data = _parse_json_response(response.content)
    data["sources"] = list(set(sources + data.get("sources", [])))

    return {
        "research_results": [{"type": "build_timeline", "data": data}]
    }


# ---------------------------------------------------------------------------
# merge_research
# ---------------------------------------------------------------------------

def merge_research(state: ResearchState) -> dict:
    results_by_type = {r["type"]: r["data"] for r in state["research_results"]}

    market = results_by_type.get("market_sizing", {})
    competitors = results_by_type.get("competitor_matrix", {})
    risks = results_by_type.get("risk_analysis", {})
    strategy = results_by_type.get("tech_marketing_strategy", {})
    usp = results_by_type.get("usp_analysis", {})
    timeline = results_by_type.get("build_timeline", {})

    all_sources = list(set(
        market.get("sources", []) +
        competitors.get("sources", []) +
        risks.get("sources", []) +
        strategy.get("sources", []) +
        usp.get("sources", []) +
        timeline.get("sources", [])
    ))

    summary_input = json.dumps({
        "market_sizing": market,
        "competitor_matrix": competitors,
        "risk_analysis": risks,
        "tech_marketing_strategy": strategy,
        "usp_analysis": usp,
        "build_timeline": timeline,
    }, indent=2)

    messages = [
        SystemMessage(content=MERGE_PROMPT),
        HumanMessage(content=f"Business idea: {state['idea']}\n\nResearch data:\n{summary_input}"),
    ]
    response = llm.invoke(messages)
    output = _parse_json_response(response.content)
    output["sources"] = list(set(all_sources + output.get("sources", [])))

    return {"research_output": output}
