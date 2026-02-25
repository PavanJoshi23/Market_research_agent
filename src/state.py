import operator
from typing import Annotated, Optional, TypedDict


class ResearchState(TypedDict):
    """
    Shared state flowing through the Research Agent graph.

    research_results uses operator.add so all 3 parallel nodes
    (market_sizing, competitor_matrix, risk_analysis) can safely
    append their output without overwriting each other.
    """
    idea: str
    research_results: Annotated[list[dict], operator.add]
    research_output: Optional[dict]
