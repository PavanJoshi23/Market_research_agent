import os

from langchain_community.utilities import SearxSearchWrapper
from langchain_core.tools import tool

search = SearxSearchWrapper(searx_host=os.environ["SEARXNG_HOST"])

MAX_SNIPPET_CHARS = 400


def _format_results(results: list[dict]) -> str:
    lines = []
    for i, r in enumerate(results, 1):
        snippet = r.get("snippet", "")[:MAX_SNIPPET_CHARS]
        lines.append(f"[{i}] {r.get('title', '')}\n    {r.get('link', '')}\n    {snippet}\n")
    return "\n".join(lines)


@tool
def web_search(query: str) -> str:
    """Search the web for information about a topic."""
    results = search.results(query, num_results=5)
    return _format_results(results)


@tool
def news_search(query: str) -> str:
    """Search recent news for regulatory, legal, or market news."""
    results = search.results(query, num_results=5, categories=["news"])
    return _format_results(results)
