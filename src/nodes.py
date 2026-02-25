import json
import os
import re

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI
from langgraph.types import interrupt

from .prompts import (
    BUILD_TIMELINE_PROMPT,
    COMPETITOR_MATRIX_PROMPT,
    FINAL_MERGE_PROMPT,
    FOLLOWUP_ANALYZER_PROMPT,
    MARKET_SIZING_PROMPT,
    MERGE_PROMPT,
    RISK_ANALYSIS_PROMPT,
    TECH_MARKETING_STRATEGY_PROMPT,
    TLDR_QUESTIONS_PROMPT,
    USP_ANALYSIS_PROMPT,
)
from .state import ResearchState
from .tools import news_search, web_search


# -------------------------------------------------------------------
# LLM
# -------------------------------------------------------------------

llm = AzureChatOpenAI(
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
    openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    temperature=1,
    streaming=False,
)


# -------------------------------------------------------------------
# Utilities
# -------------------------------------------------------------------

def _parse_json_response(content: str) -> dict:
    content = content.strip()

    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
    if fence_match:
        content = fence_match.group(1).strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    start = content.find("{")
    if start != -1:
        obj, _ = json.JSONDecoder().raw_decode(content, start)
        return obj

    raise json.JSONDecodeError("No valid JSON object found", content, 0)


def _invoke_json_agent(agent, idea: str, max_retries: int = 2) -> dict:
    last_exc: Exception = RuntimeError("no attempts made")
    for _ in range(max_retries + 1):
        content = _invoke_agent(agent, idea)
        try:
            return _parse_json_response(content)
        except (json.JSONDecodeError, ValueError) as exc:
            last_exc = exc
    raise last_exc


def _make_agent(system_prompt: str, tools: list):
    """
    Modern LangChain agent factory.
    Replaces create_tool_calling_agent + AgentExecutor.
    """
    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )


def _invoke_agent(agent, idea: str):
    """
    Standardized invocation wrapper.
    """
    result = agent.invoke(
        {
            "messages": [
                {"role": "user", "content": f"Business idea: {idea}"}
            ]
        }
    )

    return result["messages"][-1].content


# -------------------------------------------------------------------
# Graph Nodes
# -------------------------------------------------------------------

def intake(state: ResearchState) -> dict:
    idea = state["idea"].strip()
    if not idea:
        raise ValueError("Idea cannot be empty.")

    return {
        "idea": idea,
        "research_results": [],
    }


def market_sizing(state: ResearchState) -> dict:
    agent = _make_agent(MARKET_SIZING_PROMPT, [web_search])
    data = _invoke_json_agent(agent, state["idea"])
    return {"research_results": [{"type": "market_sizing", "data": data}]}


def competitor_matrix(state: ResearchState) -> dict:
    agent = _make_agent(COMPETITOR_MATRIX_PROMPT, [web_search])
    data = _invoke_json_agent(agent, state["idea"])
    return {"research_results": [{"type": "competitor_matrix", "data": data}]}


def risk_analysis(state: ResearchState) -> dict:
    agent = _make_agent(RISK_ANALYSIS_PROMPT, [web_search, news_search])
    data = _invoke_json_agent(agent, state["idea"])
    return {"research_results": [{"type": "risk_analysis", "data": data}]}


def tech_marketing_strategy(state: ResearchState) -> dict:
    agent = _make_agent(TECH_MARKETING_STRATEGY_PROMPT, [web_search])
    data = _invoke_json_agent(agent, state["idea"])
    return {"research_results": [{"type": "tech_marketing_strategy", "data": data}]}


def usp_analysis(state: ResearchState) -> dict:
    agent = _make_agent(USP_ANALYSIS_PROMPT, [web_search])
    data = _invoke_json_agent(agent, state["idea"])
    return {"research_results": [{"type": "usp_analysis", "data": data}]}


def build_timeline(state: ResearchState) -> dict:
    agent = _make_agent(BUILD_TIMELINE_PROMPT, [web_search])
    data = _invoke_json_agent(agent, state["idea"])
    return {"research_results": [{"type": "build_timeline", "data": data}]}


# -------------------------------------------------------------------
# Merge Phase
# -------------------------------------------------------------------

def merge_research(state: ResearchState) -> dict:
    results_by_type = {
        r["type"]: r["data"]
        for r in state["research_results"]
    }

    summary_input = json.dumps(
        {
            "market_sizing": results_by_type.get("market_sizing", {}),
            "competitor_matrix": results_by_type.get("competitor_matrix", {}),
            "risk_analysis": results_by_type.get("risk_analysis", {}),
            "tech_marketing_strategy": results_by_type.get("tech_marketing_strategy", {}),
            "usp_analysis": results_by_type.get("usp_analysis", {}),
            "build_timeline": results_by_type.get("build_timeline", {}),
        },
        indent=2,
    )

    messages = [
        SystemMessage(content=MERGE_PROMPT),
        HumanMessage(
            content=f"Business idea: {state['idea']}\n\nResearch data:\n{summary_input}"
        ),
    ]

    response = llm.invoke(messages)
    output = _parse_json_response(response.content)

    return {"research_output": output}


# -------------------------------------------------------------------
# TLDR + Followup Loop
# -------------------------------------------------------------------

def generate_tldr_questions(state: ResearchState) -> dict:
    output = state["research_output"]

    messages = [
        SystemMessage(content=TLDR_QUESTIONS_PROMPT),
        HumanMessage(content=f"Research output:\n{json.dumps(output, indent=2)}"),
    ]

    response = llm.invoke(messages)
    data = _parse_json_response(response.content)

    tldr = data.get("tldr", "")
    questions = data.get("questions", [])

    user_answers = interrupt(
        {
            "tldr": tldr,
            "questions": questions,
        }
    )

    return {
        "tldr": tldr,
        "clarifying_questions": questions,
        "user_answers": user_answers,
    }


def analyze_followup(state: ResearchState) -> dict:
    messages = [
        SystemMessage(content=FOLLOWUP_ANALYZER_PROMPT),
        HumanMessage(
            content=(
                f"User's answers: {state['user_answers']}\n\n"
                f"Turn 1 research summary:\n"
                f"{json.dumps(state['research_output'], indent=2)}"
            )
        ),
    ]

    response = llm.invoke(messages)
    data = _parse_json_response(response.content)

    valid_nodes = {
        "market_sizing",
        "competitor_matrix",
        "risk_analysis",
        "tech_marketing_strategy",
        "usp_analysis",
        "build_timeline",
    }

    nodes = [
        n for n in data.get("follow_up_nodes", [])
        if n in valid_nodes
    ]

    if not nodes:
        nodes = ["market_sizing"]

    return {"follow_up_nodes": nodes}


def final_merge(state: ResearchState) -> dict:
    turn2_by_type = {
        r["type"]: r["data"]
        for r in (state.get("followup_results") or [])
    }

    base = state["research_output"] or {}

    summary_input = json.dumps(
        {
            "turn1_output": base,
            "turn2_updates": turn2_by_type,
            "user_answers": state.get("user_answers", ""),
        },
        indent=2,
    )

    messages = [
        SystemMessage(content=FINAL_MERGE_PROMPT),
        HumanMessage(
            content=f"Business idea: {state['idea']}\n\nData:\n{summary_input}"
        ),
    ]

    response = llm.invoke(messages)
    output = _parse_json_response(response.content)

    return {"research_output": output}