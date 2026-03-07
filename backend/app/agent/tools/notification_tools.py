"""Notification tools — agent can notify or ask the user."""

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from services.store import store


@tool
def notify_user(title: str, message: str, notification_type: str = "info") -> str:
    """Send a notification to the user. Does NOT pause the agent.

    Use this to report completed actions, status updates, or errors.
    notification_type: "info", "action_taken", or "error"
    """
    store.add_notification({
        "type": notification_type,
        "title": title,
        "message": message,
    })
    return "Notification sent."


@tool
def ask_user(question: str, context: str = "", config: RunnableConfig = None) -> str:
    """Ask the user a question and wait for their response.

    Use when you genuinely need information only the user can provide.
    Do NOT use for permission to read data — just read it.
    This PAUSES the agent until the user replies.
    """
    from langgraph.types import interrupt

    # Extract session_id from config so the reply endpoint can resume
    session_id = None
    if config and "configurable" in config:
        session_id = config["configurable"].get("thread_id")

    # Store a question notification before pausing
    store.add_notification({
        "type": "question",
        "title": "Agent needs your input",
        "message": question,
        "session_id": session_id,
    })

    # interrupt() pauses the graph; when resumed via Command(resume=answer), returns the answer
    answer = interrupt({"question": question, "context": context})
    return answer
