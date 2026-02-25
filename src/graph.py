"""
LangGraph StateGraph for the I2M Research Agent.

Topology:
  START → intake → [research_router]
                       ├─ Send("market_sizing")
                       ├─ Send("competitor_matrix")
                       ├─ Send("risk_analysis")
                       ├─ Send("tech_marketing_strategy")
                       ├─ Send("usp_analysis")
                       └─ Send("build_timeline")
                             ↓ (all 6 complete, state merged)
                       merge_research → END

The Send() primitive fires all six sub-agents in parallel.
Their results accumulate into research_results via operator.add reducer.
"""

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from .nodes import (
    build_timeline,
    competitor_matrix,
    intake,
    market_sizing,
    merge_research,
    risk_analysis,
    tech_marketing_strategy,
    usp_analysis,
)
from .state import ResearchState


# ---------------------------------------------------------------------------
# Routing function — fans out to 6 parallel sub-agents via Send()
# ---------------------------------------------------------------------------

def research_router(state: ResearchState) -> list[Send]:
    """
    After intake, fire all six research sub-tasks simultaneously.
    LangGraph executes these in parallel and merges their state updates.
    """
    return [
        Send("market_sizing", state),
        Send("competitor_matrix", state),
        Send("risk_analysis", state),
        Send("tech_marketing_strategy", state),
        Send("usp_analysis", state),
        Send("build_timeline", state),
    ]


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

def build_graph():
    graph = StateGraph(ResearchState)

    # Register nodes
    graph.add_node("intake", intake)
    graph.add_node("market_sizing", market_sizing)
    graph.add_node("competitor_matrix", competitor_matrix)
    graph.add_node("risk_analysis", risk_analysis)
    graph.add_node("tech_marketing_strategy", tech_marketing_strategy)
    graph.add_node("usp_analysis", usp_analysis)
    graph.add_node("build_timeline", build_timeline)
    graph.add_node("merge_research", merge_research)

    # Edges
    graph.add_edge(START, "intake")

    # Fan-out: intake → 6 parallel sub-agents via conditional edge + Send()
    graph.add_conditional_edges("intake", research_router)

    # Fan-in: all 6 sub-agents → merge_research
    graph.add_edge("market_sizing", "merge_research")
    graph.add_edge("competitor_matrix", "merge_research")
    graph.add_edge("risk_analysis", "merge_research")
    graph.add_edge("tech_marketing_strategy", "merge_research")
    graph.add_edge("usp_analysis", "merge_research")
    graph.add_edge("build_timeline", "merge_research")

    graph.add_edge("merge_research", END)

    return graph.compile()


# Compiled graph — import this in main.py
research_graph = build_graph()
