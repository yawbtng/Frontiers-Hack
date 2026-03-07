"""SSE event formatting and graph streaming bridge."""

import json
import logging
from typing import Any, AsyncGenerator, Union

from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from models.events import (
    ApprovalRequiredEvent,
    DoneEvent,
    ErrorEvent,
    StatusEvent,
    TokenEvent,
    ToolResultEvent,
)

logger = logging.getLogger(__name__)

SSEEvent = Union[
    StatusEvent, TokenEvent, ToolResultEvent,
    ApprovalRequiredEvent, DoneEvent, ErrorEvent,
]


def format_sse_event(event: BaseModel) -> str:
    """Format a Pydantic event model as an SSE string."""
    data = event.model_dump()
    event_type = data.get("type", "message")
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


async def run_graph_with_streaming(
    graph: Any,
    session_id: str,
    user_id: str,
    message: str,
) -> AsyncGenerator[str, None]:
    """Run the FRIDAY graph and yield SSE-formatted strings."""
    config = {
        "configurable": {
            "thread_id": session_id,
            "user_id": user_id,
        }
    }
    input_state = {
        "messages": [HumanMessage(content=message)],
        "session_id": session_id,
        "user_id": user_id,
    }

    yield format_sse_event(StatusEvent(message="Processing your message..."))

    try:
        async for event in graph.astream_events(
            input_state, config=config, version="v2"
        ):
            kind = event.get("event", "")
            name = event.get("name", "")

            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    yield format_sse_event(TokenEvent(content=chunk.content))

            elif kind == "on_tool_start":
                yield format_sse_event(StatusEvent(message=f"Using {name}..."))

            elif kind == "on_tool_end":
                output = event.get("data", {}).get("output", "")
                result_str = str(output)[:500]
                yield format_sse_event(
                    ToolResultEvent(tool_name=name, result=result_str)
                )

        # Check for interrupts (approval required)
        state = await graph.aget_state(config)
        if state and hasattr(state, "tasks") and state.tasks:
            for task in state.tasks:
                if hasattr(task, "interrupts") and task.interrupts:
                    for intr in task.interrupts:
                        payload = intr.value if hasattr(intr, "value") else intr
                        if isinstance(payload, dict):
                            yield format_sse_event(
                                ApprovalRequiredEvent(
                                    action_type=payload.get("action_type", "unknown"),
                                    payload=payload,
                                    explanation=payload.get("explanation", ""),
                                    dry_run_result=payload.get("dry_run_result"),
                                )
                            )

        yield format_sse_event(DoneEvent(session_id=session_id))

    except Exception as e:
        logger.error(f"Graph streaming error: {e}", exc_info=True)
        yield format_sse_event(ErrorEvent(message=str(e)))


async def resume_graph_with_streaming(
    graph: Any,
    session_id: str,
    user_id: str,
    approval_result: dict,
) -> AsyncGenerator[str, None]:
    """Resume the FRIDAY graph after an approval decision."""
    from langgraph.types import Command

    config = {
        "configurable": {
            "thread_id": session_id,
            "user_id": user_id,
        }
    }

    status_msg = "Processing approval..." if approval_result.get("approved") else "Cancelling action..."
    yield format_sse_event(StatusEvent(message=status_msg))

    try:
        async for event in graph.astream_events(
            Command(resume=approval_result), config=config, version="v2"
        ):
            kind = event.get("event", "")
            name = event.get("name", "")

            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    yield format_sse_event(TokenEvent(content=chunk.content))

            elif kind == "on_tool_start":
                yield format_sse_event(StatusEvent(message=f"Using {name}..."))

            elif kind == "on_tool_end":
                output = event.get("data", {}).get("output", "")
                result_str = str(output)[:500]
                yield format_sse_event(
                    ToolResultEvent(tool_name=name, result=result_str)
                )

        yield format_sse_event(DoneEvent(session_id=session_id))

    except Exception as e:
        logger.error(f"Graph resume error: {e}", exc_info=True)
        yield format_sse_event(ErrorEvent(message=str(e)))
