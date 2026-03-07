import logging

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage

from models.schemas import ChatRequest
from services.store import store

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


def _get_graph():
    """Lazy import to avoid circular imports at module level."""
    from agent.graph import friday_graph
    return friday_graph


@router.post("/")
async def chat(request: ChatRequest):
    """Send a message to FRIDAY and get a complete response.

    The agent autonomously decides what tools to call and loops
    until it has a final response. No separate approval step needed
    for read operations.
    """
    graph = _get_graph()

    # Create or retrieve session
    session_id = request.session_id
    if not session_id:
        session = store.create_session(request.user_id)
        session_id = session["session_id"]
    elif not store.get_session(session_id):
        store.create_session(request.user_id, session_id=session_id)

    # Save user message
    store.add_message(session_id, "user", request.message)

    config = {
        "configurable": {
            "thread_id": session_id,
            "user_id": request.user_id,
        },
        "recursion_limit": 25,  # Max tool-calling iterations
    }
    input_state = {
        "messages": [HumanMessage(content=request.message)],
        "session_id": session_id,
        "user_id": request.user_id,
    }

    try:
        result = await graph.ainvoke(input_state, config=config)

        # Extract the final AI response from messages
        response_text = ""
        if result.get("messages"):
            for msg in reversed(result["messages"]):
                if hasattr(msg, "type") and msg.type == "ai" and msg.content:
                    response_text = msg.content
                    break

        return {
            "response": response_text,
            "session_id": session_id,
            "intent": result.get("intent", "chat"),
        }

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
