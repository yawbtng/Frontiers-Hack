"""Notifications API — list, reply, dismiss, mark-read."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langgraph.types import Command

from services.store import store

router = APIRouter()


class ReplyRequest(BaseModel):
    message: str


# ---------- Endpoints ----------


@router.get("")
async def list_notifications(limit: int = 50):
    """Get recent notifications, most recent first."""
    return store.get_notifications(limit=limit)


@router.get("/unread-count")
async def unread_count():
    """Get count of unread notifications."""
    return {"count": store.get_unread_count()}


@router.post("/{notification_id}/reply")
async def reply_to_notification(notification_id: str, body: ReplyRequest):
    """Reply to a question notification and resume the agent graph."""
    notif = store.get_notification(notification_id)
    if not notif or notif["type"] != "question":
        raise HTTPException(404, "Not a question notification")

    if not notif.get("session_id"):
        raise HTTPException(400, "No session_id to resume")

    from agent.graph import friday_graph

    config = {
        "configurable": {"thread_id": notif["session_id"], "user_id": "default"},
        "recursion_limit": 40,
    }

    # Resume the graph — the interrupt() in ask_user receives this value
    await friday_graph.ainvoke(Command(resume=body.message), config=config)

    store.update_notification(notification_id, status="answered")

    # Check if graph paused again (another question)
    graph_state = await friday_graph.aget_state(config)
    still_waiting = bool(graph_state and graph_state.next)

    return {"status": "resumed", "still_waiting": still_waiting}


@router.post("/{notification_id}/dismiss")
async def dismiss_notification(notification_id: str):
    """Dismiss a notification."""
    notif = store.update_notification(notification_id, status="dismissed")
    if not notif:
        raise HTTPException(404, "Notification not found")
    return {"status": "dismissed"}


@router.post("/mark-read")
async def mark_all_read():
    """Mark all unread notifications as read."""
    for n in store.notifications:
        if n["status"] == "unread":
            n["status"] = "read"
    return {"status": "ok"}
