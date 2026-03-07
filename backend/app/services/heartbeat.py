"""Heartbeat — autonomous meeting scanner and proactive trigger."""

import asyncio
import logging

from langchain_core.messages import HumanMessage

from services.store import store

logger = logging.getLogger(__name__)


async def heartbeat_loop(interval: int = 600):
    """Background loop that scans unprocessed meetings periodically."""
    while True:
        try:
            await asyncio.sleep(interval)
            await scan_unprocessed_meetings()
        except asyncio.CancelledError:
            logger.info("Heartbeat loop cancelled")
            break
        except Exception as e:
            logger.warning(f"Heartbeat error: {e}")
            await asyncio.sleep(10)


async def scan_unprocessed_meetings():
    """Find meetings that haven't been scanned yet and process them."""
    from db import DatabaseManager

    db = DatabaseManager()
    meetings = await db.get_all_meetings()

    for meeting in meetings:
        mid = meeting["id"]
        if store.is_meeting_scanned(mid):
            continue
        await process_meeting(mid, meeting.get("title", "Untitled"))
        store.mark_meeting_scanned(mid)
        await asyncio.sleep(2)  # Rate limit between meetings


async def process_meeting(meeting_id: str, title: str):
    """Send full transcript to the agent for autonomous processing."""
    from db import DatabaseManager
    from agent.graph import friday_graph

    db = DatabaseManager()
    meeting_data = await db.get_meeting(meeting_id)
    if not meeting_data or not meeting_data.get("transcripts"):
        return

    transcript_text = "\n".join(
        t["text"] for t in meeting_data["transcripts"] if t.get("text")
    )
    if not transcript_text.strip():
        return

    session_id = f"proactive-{meeting_id}"
    config = {
        "configurable": {"thread_id": session_id, "user_id": "default"},
        "recursion_limit": 40,
    }
    input_state = {
        "messages": [
            HumanMessage(
                content=(
                    f"Process this meeting transcript and execute all action items:\n\n"
                    f"---\nMeeting: {title}\n---\n{transcript_text[:8000]}"
                )
            )
        ],
        "session_id": session_id,
        "user_id": "default",
        "intent": "proactive",
    }

    try:
        result = await friday_graph.ainvoke(input_state, config=config)

        # Check if graph was interrupted (agent asked a question)
        graph_state = await friday_graph.aget_state(config)
        if graph_state and graph_state.next:
            # Graph is paused — notification was already stored by ask_user tool
            pass
        else:
            store.add_notification({
                "type": "info",
                "title": f"Processed '{title}'",
                "message": "Meeting scan complete.",
                "meeting_id": meeting_id,
                "session_id": session_id,
            })
    except Exception as e:
        logger.error(f"Error processing meeting '{title}': {e}")
        store.add_notification({
            "type": "error",
            "title": f"Error processing '{title}'",
            "message": str(e)[:300],
            "meeting_id": meeting_id,
        })


async def trigger_meeting_scan(meeting_id: str, title: str):
    """Called directly when a recording finishes. Skips the timer."""
    if store.is_meeting_scanned(meeting_id):
        return
    await process_meeting(meeting_id, title)
    store.mark_meeting_scanned(meeting_id)
