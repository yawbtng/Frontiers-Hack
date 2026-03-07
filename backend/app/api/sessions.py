from fastapi import APIRouter, HTTPException, Query

from models.schemas import SessionResponse
from services.store import store

router = APIRouter(tags=["sessions"])


@router.get("/")
async def list_sessions(user_id: str = Query(default="default")):
    """List user sessions, most recent first."""
    sessions = store.list_sessions(user_id)
    result = []
    for s in sessions:
        sid = s["session_id"]
        msg_count = len(store.get_messages(sid))
        result.append({
            **s,
            "message_count": msg_count,
        })
    return result


@router.get("/{session_id}")
async def get_session(session_id: str):
    """Get a session with its message history."""
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = store.get_messages(session_id)
    return {
        **session,
        "messages": messages,
        "message_count": len(messages),
    }
