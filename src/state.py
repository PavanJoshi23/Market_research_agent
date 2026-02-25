import operator
from typing import Annotated, Optional, TypedDict


class ResearchState(TypedDict):
    idea: str
    research_results: Annotated[list[dict], operator.add]
    research_output: Optional[dict]
    tldr: Optional[str]
    clarifying_questions: Optional[list[str]]
    user_answers: Optional[str]
    follow_up_nodes: Optional[list[str]]
    followup_results: Optional[list[dict]]
