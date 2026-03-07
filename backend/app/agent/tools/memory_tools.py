import json
import logging
from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

_sm_client = None
try:
    from config import settings
    if settings.supermemory_api_key:
        from supermemory import AsyncSupermemory
        _sm_client = AsyncSupermemory(api_key=settings.supermemory_api_key)
except Exception as e:
    logger.warning(f"Supermemory not available: {e}")


def _get_user_id(config: RunnableConfig) -> str:
    return config.get("configurable", {}).get("user_id", "default")


@tool
async def memory_search(config: RunnableConfig, query: str, limit: int = 5) -> str:
    """Search the user's semantic memory for relevant past context.

    Use this to recall:
    - Past conversations and commitments
    - User preferences and patterns
    - Previously discussed topics
    - Meeting summaries and notes

    Args:
        query: What to search for
        limit: Max results to return
    """
    if _sm_client is None:
        return "Memory search not available (SUPERMEMORY_API_KEY not configured)"

    user_id = _get_user_id(config)
    try:
        results = await _sm_client.search.execute(
            q=query,
            container_tags=[user_id],
            limit=limit,
        )
        if hasattr(results, 'results'):
            return json.dumps([
                {"content": r.content, "score": getattr(r, 'score', None)}
                for r in results.results
            ], default=str)
        return json.dumps(results, default=str)
    except Exception as e:
        logger.error(f"Memory search error: {e}")
        return f"Memory search error: {e}"


@tool
async def memory_store(config: RunnableConfig, content: str, metadata: Optional[str] = None) -> str:
    """Store information in the user's semantic memory for future recall.

    Use this to remember:
    - Important user statements or commitments
    - Learned patterns about the user
    - Meeting summaries or key decisions
    - User preferences discovered during conversation

    Args:
        content: The text content to store
        metadata: Optional JSON string of metadata (e.g. '{"source": "meeting", "topic": "project_x"}')
    """
    if _sm_client is None:
        return "Memory storage not available (SUPERMEMORY_API_KEY not configured)"

    user_id = _get_user_id(config)
    meta = {}
    if metadata:
        try:
            meta = json.loads(metadata)
        except (json.JSONDecodeError, TypeError):
            meta = {"raw": metadata}

    try:
        result = await _sm_client.add(
            content=content,
            container_tag=user_id,
            metadata=meta,
        )
        return json.dumps({"status": "stored", "result": result}, default=str)
    except Exception as e:
        logger.error(f"Memory store error: {e}")
        return f"Memory store error: {e}"
