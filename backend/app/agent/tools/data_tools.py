import json
from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from services.store import store


def _get_user_id(config: RunnableConfig) -> str:
    return config.get("configurable", {}).get("user_id", "default")


@tool
def get_user_tasks(
    config: RunnableConfig,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 20,
) -> str:
    """Get the user's tasks, optionally filtered by status and priority.

    Args:
        status: Filter by status (pending, in_progress, done, cancelled)
        priority: Filter by priority (low, medium, high, urgent)
        limit: Maximum number of tasks to return
    """
    user_id = _get_user_id(config)
    tasks = store.get_tasks(user_id, status=status, priority=priority, limit=limit)
    if not tasks:
        return "No tasks found."
    return json.dumps(tasks, indent=2, default=str)


@tool
def create_task(
    config: RunnableConfig,
    title: str,
    description: Optional[str] = None,
    priority: str = "medium",
    due_at: Optional[str] = None,
    source: Optional[str] = None,
    source_ref: Optional[str] = None,
) -> str:
    """Create a new task for the user.

    Args:
        title: Task title
        description: Optional description
        priority: Priority level (low, medium, high, urgent)
        due_at: Optional due date (ISO format)
        source: Where the task came from (e.g. "meeting", "email", "user")
        source_ref: Reference ID from the source
    """
    user_id = _get_user_id(config)
    task = store.create_task(
        user_id=user_id,
        title=title,
        description=description,
        priority=priority,
        due_at=due_at,
        source=source,
        source_ref=source_ref,
    )
    return json.dumps(task, default=str)


@tool
def update_task(
    config: RunnableConfig,
    task_id: str,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    title: Optional[str] = None,
) -> str:
    """Update an existing task.

    Args:
        task_id: ID of the task to update
        status: New status (pending, in_progress, done, cancelled)
        priority: New priority (low, medium, high, urgent)
        title: New title
    """
    user_id = _get_user_id(config)
    task = store.update_task(user_id, task_id, status=status, priority=priority, title=title)
    if not task:
        return f"Task {task_id} not found."
    return json.dumps(task, default=str)


@tool
def get_user_context(config: RunnableConfig, context_key: str) -> str:
    """Get a specific user context/preference value.

    Common keys: "communication_style", "work_hours", "priorities", "preferences"

    Args:
        context_key: The context key to look up
    """
    user_id = _get_user_id(config)
    ctx = store.get_user_context(user_id, context_key)
    if not ctx:
        return f"No context found for key '{context_key}'."
    return json.dumps(ctx, default=str)


@tool
def save_user_context(
    config: RunnableConfig,
    context_key: str,
    context_value: str,
    confidence: float = 0.8,
    source: str = "agent",
) -> str:
    """Save a user context/preference for future reference.

    Use this to remember things about the user like preferences, patterns,
    communication style, work schedule, etc.

    Args:
        context_key: The context key (e.g. "communication_style", "work_hours")
        context_value: JSON string of the context value
        confidence: Confidence level (0.0-1.0)
        source: Source of the context (e.g. "agent", "user", "meeting")
    """
    user_id = _get_user_id(config)
    try:
        value = json.loads(context_value)
    except (json.JSONDecodeError, TypeError):
        value = {"value": context_value}

    entry = store.save_user_context(
        user_id=user_id,
        context_key=context_key,
        context_value=value,
        confidence=confidence,
        source=source,
    )
    return json.dumps(entry, default=str)
