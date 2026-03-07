"""Tool registry — all tools available to the agent at all times."""

from .gws import gws, gws_help, gws_schema
from .exa_tools import exa_search
from .data_tools import get_user_tasks, create_task, update_task, get_user_context, save_user_context
from .memory_tools import memory_search, memory_store
from .notification_tools import notify_user, ask_user

# All tools are always available. The agent decides what to use based on context.
ALL_TOOLS: list = [
    gws,
    gws_help,
    gws_schema,
    exa_search,
    get_user_tasks,
    create_task,
    update_task,
    get_user_context,
    save_user_context,
    memory_search,
    memory_store,
    notify_user,
    ask_user,
]
