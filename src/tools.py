"""
Tavily search tool instances — one per research sub-task,
each tuned with different depth/topic settings to best fit
the kind of queries it will run.
"""

from langchain_tavily import TavilySearch

# Market sizing: advanced depth for richer snippets on TAM/SAM/SOM data
market_tool = TavilySearch(
    max_results=7,
    search_depth="advanced",
    include_answer=True,
    topic="general",
)

# Competitor matrix: advanced depth, higher result count for broad coverage
competitor_tool = TavilySearch(
    max_results=8,
    search_depth="advanced",
    include_answer=True,
    topic="general",
)

# Risk analysis: basic depth but scoped to recent news for current regulatory landscape
risk_tool = TavilySearch(
    max_results=6,
    search_depth="basic",
    include_answer=True,
    topic="news",
    time_range="year",
)

# Strategy & USP: advanced depth for tech stack, GTM, and differentiation research
strategy_tool = TavilySearch(
    max_results=7,
    search_depth="advanced",
    include_answer=True,
    topic="general",
)
