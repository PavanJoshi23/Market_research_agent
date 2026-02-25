from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from .nodes import (
    analyze_followup,
    build_timeline,
    competitor_matrix,
    final_merge,
    generate_tldr_questions,
    intake,
    market_sizing,
    merge_research,
    risk_analysis,
    tech_marketing_strategy,
    usp_analysis,
)
from .state import ResearchState

_ALL_RESEARCH_NODES = [
    "market_sizing",
    "competitor_matrix",
    "risk_analysis",
    "tech_marketing_strategy",
    "usp_analysis",
    "build_timeline",
]

_NODE_FUNCS = {
    "market_sizing": market_sizing,
    "competitor_matrix": competitor_matrix,
    "risk_analysis": risk_analysis,
    "tech_marketing_strategy": tech_marketing_strategy,
    "usp_analysis": usp_analysis,
    "build_timeline": build_timeline,
}


def research_router(state: ResearchState) -> list[Send]:
    return [Send(node, state) for node in _ALL_RESEARCH_NODES]


def followup_research(state: ResearchState) -> dict:
    new_results = []
    for node_name in (state["follow_up_nodes"] or []):
        fn = _NODE_FUNCS.get(node_name)
        if fn:
            result = fn(state)
            new_results.extend(result.get("research_results", []))
    return {"followup_results": new_results}


def build_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("intake", intake)
    graph.add_node("market_sizing", market_sizing)
    graph.add_node("competitor_matrix", competitor_matrix)
    graph.add_node("risk_analysis", risk_analysis)
    graph.add_node("tech_marketing_strategy", tech_marketing_strategy)
    graph.add_node("usp_analysis", usp_analysis)
    graph.add_node("build_timeline", build_timeline)
    graph.add_node("merge_research", merge_research)
    graph.add_node("generate_tldr_questions", generate_tldr_questions)
    graph.add_node("analyze_followup", analyze_followup)
    graph.add_node("followup_research", followup_research)
    graph.add_node("final_merge", final_merge)

    graph.add_edge(START, "intake")
    graph.add_conditional_edges("intake", research_router)

    for node in _ALL_RESEARCH_NODES:
        graph.add_edge(node, "merge_research")

    graph.add_edge("merge_research", "generate_tldr_questions")
    graph.add_edge("generate_tldr_questions", "analyze_followup")
    graph.add_edge("analyze_followup", "followup_research")
    graph.add_edge("followup_research", "final_merge")
    graph.add_edge("final_merge", END)

    return graph.compile(checkpointer=MemorySaver())


research_graph = build_graph()
