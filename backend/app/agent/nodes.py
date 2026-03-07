"""FRIDAY agent nodes — ReAct loop with autonomous tool execution."""

import json
import logging

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from config import settings
from services.store import store

from .prompts import build_system_prompt, TRIAGE_KEYWORDS
from .tools.registry import ALL_TOOLS

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# ---------- LLM singletons ----------

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model="google/gemini-2.5-flash",
            api_key=settings.openrouter_api_key,
            base_url=OPENROUTER_BASE_URL,
            temperature=0.3,
        )
    return _llm


# ---------- Helper ----------

def _extract_text(msg) -> str:
    """Extract plain text from a message, handling multimodal content blocks."""
    raw = msg.content if hasattr(msg, "content") else str(msg)
    if isinstance(raw, list):
        return " ".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in raw
        )
    return str(raw)


def _detect_intent(text: str) -> str:
    """Fast keyword-based intent detection. No LLM call needed."""
    text_lower = text.lower()
    for keyword in TRIAGE_KEYWORDS:
        if keyword in text_lower:
            return "triage"
    return "chat"


# ---------- Nodes ----------

async def preprocess_node(state: dict) -> dict:
    """Load user context, tasks, and semantic memory."""
    user_id = state.get("user_id", "default")

    # Load user context from in-memory store
    user_context_list = store.get_user_context(user_id)
    if isinstance(user_context_list, list):
        user_context = {
            entry.get("context_key", str(i)): entry
            for i, entry in enumerate(user_context_list)
        }
    else:
        user_context = user_context_list if isinstance(user_context_list, dict) else {}

    # Load active tasks
    active_tasks = store.get_tasks(user_id, status="pending", limit=10)
    active_tasks += store.get_tasks(user_id, status="in_progress", limit=10)

    # Search semantic memory
    semantic_context = []
    messages = state.get("messages", [])
    if messages:
        content = _extract_text(messages[-1])
        try:
            from .tools.memory_tools import _sm_client
            if _sm_client:
                results = await _sm_client.search.execute(
                    q=content[:500],
                    container_tags=[user_id],
                    limit=3,
                )
                if hasattr(results, "results"):
                    semantic_context = [
                        {"content": r.content or "", "score": getattr(r, "score", None)}
                        for r in results.results
                        if r.content
                    ]
        except Exception as e:
            logger.warning(f"Semantic memory search failed: {e}")

    # Detect triage intent from last message
    last_text = _extract_text(messages[-1]) if messages else ""
    intent = _detect_intent(last_text)

    # Trim messages to last 20
    trimmed = messages[-20:] if len(messages) > 20 else messages

    return {
        "user_context": user_context,
        "active_tasks": active_tasks,
        "semantic_context": semantic_context,
        "messages": trimmed,
        "intent": intent,
    }


async def agent_node(state: dict) -> dict:
    """Core ReAct agent: call LLM with tools, let it decide what to do.

    The LLM either:
    - Returns tool_calls → routes to tool_executor (loop continues)
    - Returns text response → routes to postprocess (loop ends)
    """
    llm = _get_llm()
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    system_prompt = build_system_prompt(state)
    msgs = [SystemMessage(content=system_prompt)] + list(state.get("messages", []))

    response = await llm_with_tools.ainvoke(msgs)

    return {"messages": [response]}


async def tool_executor_node(state: dict) -> dict:
    """Execute tool calls from the agent's last message."""
    messages = state.get("messages", [])
    last_msg = messages[-1]

    if not hasattr(last_msg, "tool_calls") or not last_msg.tool_calls:
        return {}

    tool_map = {t.name: t for t in ALL_TOOLS}
    new_messages = []
    user_id = state.get("user_id", "default")

    for tc in last_msg.tool_calls:
        tool_name = tc["name"]
        tool_args = tc["args"]

        if tool_name not in tool_map:
            new_messages.append(ToolMessage(
                content=f"Unknown tool: '{tool_name}'. Available tools: {', '.join(tool_map.keys())}",
                tool_call_id=tc["id"],
            ))
            continue

        try:
            config = {"configurable": {"user_id": user_id}}
            result = await tool_map[tool_name].ainvoke(tool_args, config=config)
            new_messages.append(ToolMessage(
                content=str(result),
                tool_call_id=tc["id"],
            ))
        except Exception as e:
            logger.error(f"Tool error ({tool_name}): {e}")
            new_messages.append(ToolMessage(
                content=f"Error executing {tool_name}: {e}. Try a different approach or check the command syntax with gws_schema.",
                tool_call_id=tc["id"],
            ))

    return {"messages": new_messages}


def should_continue(state: dict) -> str:
    """Route after agent: if tool calls exist, loop back; otherwise finish."""
    messages = state.get("messages", [])
    if not messages:
        return "postprocess"

    last_msg = messages[-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"
    return "postprocess"


async def postprocess_node(state: dict) -> dict:
    """Save session data and learn patterns."""
    session_id = state.get("session_id", "")
    user_id = state.get("user_id", "default")

    # Save last assistant message
    messages = state.get("messages", [])
    if messages:
        last_msg = messages[-1]
        if hasattr(last_msg, "type") and last_msg.type == "ai" and last_msg.content:
            store.add_message(session_id, "assistant", last_msg.content)

    store.update_session(session_id)

    # Store session summary to semantic memory if tools were used
    tool_msgs = [m for m in messages[-10:] if hasattr(m, "type") and m.type == "tool"]
    if tool_msgs:
        try:
            from .tools.memory_tools import _sm_client
            if _sm_client:
                # Build a brief summary from the last AI message
                last_ai = None
                for m in reversed(messages):
                    if hasattr(m, "type") and m.type == "ai" and m.content:
                        last_ai = m
                        break

                if last_ai:
                    summary = f"Session {session_id}: {last_ai.content[:200]}"
                    await _sm_client.add(
                        content=summary,
                        container_tag=user_id,
                        metadata={"type": "session_summary", "session_id": session_id},
                    )
        except Exception as e:
            logger.warning(f"Failed to store session summary: {e}")

    return {}
