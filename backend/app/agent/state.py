"""FRIDAY agent state definition."""

from typing import Literal, Optional
from pydantic import Field
from langgraph.graph import MessagesState


class FridayState(MessagesState):
    """Extended state for the FRIDAY agent graph.

    Uses MessagesState which provides `messages` with the add_messages reducer.
    The agent follows a ReAct loop: agent -> tools -> agent (repeat until done).
    """
    session_id: str = ""
    user_id: str = ""
    user_context: dict = Field(default_factory=dict)
    active_tasks: list[dict] = Field(default_factory=list)
    semantic_context: list[dict] = Field(default_factory=list)
    intent: Optional[Literal["chat", "triage", "proactive"]] = None
    error: Optional[str] = None
