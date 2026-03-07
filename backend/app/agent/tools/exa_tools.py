"""Exa neural web search tool for LangGraph agent."""

import asyncio
import json
import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

_exa_client = None


def _get_exa_client():
    global _exa_client
    if _exa_client is None:
        from config import settings
        if not settings.exa_api_key:
            return None
        from exa_py import Exa
        _exa_client = Exa(api_key=settings.exa_api_key)
    return _exa_client


def _sync_exa_search(query: str, num_results: int):
    """Synchronous Exa search to be run in a thread."""
    client = _get_exa_client()
    if client is None:
        return {"error": "Exa API key not configured"}

    result = client.search_and_contents(
        query=query,
        num_results=num_results,
        text={"max_characters": 1000},
        use_autoprompt=True,
    )
    results = []
    for r in result.results:
        results.append({
            "title": r.title,
            "url": r.url,
            "text": r.text[:500] if r.text else "",
            "score": getattr(r, "score", None),
        })
    return results


@tool
async def exa_search(
    query: str,
    num_results: int = 5,
) -> str:
    """Search the web for real-time information using Exa's neural search.

    Use this when the user's question requires information BEYOND their
    Google Workspace — news, research, documentation, public information,
    company lookups, industry trends, etc.

    Do NOT use this for:
    - User's emails, calendar, or docs — use gws tools instead
    - User's tasks or preferences — use data_tools instead
    """
    try:
        results = await asyncio.to_thread(_sync_exa_search, query, num_results)
        return json.dumps(results)
    except Exception as e:
        logger.error("Exa search failed: %s", e)
        return json.dumps({"error": str(e)})
