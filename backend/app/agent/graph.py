"""FRIDAY agent graph — ReAct loop architecture.

Graph structure:
    START → preprocess → agent ←→ tools (loop) → postprocess → END

The agent autonomously decides when to call tools and when to respond.
No separate intent classifier LLM call — just keyword-based triage detection.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END

from .state import FridayState
from .nodes import (
    preprocess_node,
    agent_node,
    tool_executor_node,
    postprocess_node,
    should_continue,
)

# Build the graph
graph = StateGraph(FridayState)

# Nodes
graph.add_node("preprocess", preprocess_node)
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_executor_node)
graph.add_node("postprocess", postprocess_node)

# Edges
graph.add_edge(START, "preprocess")
graph.add_edge("preprocess", "agent")
graph.add_conditional_edges(
    "agent",
    should_continue,
    {"tools": "tools", "postprocess": "postprocess"},
)
graph.add_edge("tools", "agent")  # ReAct loop: tools always go back to agent
graph.add_edge("postprocess", END)

# Compile with checkpointer for FastAPI standalone mode
checkpointer = MemorySaver()
friday_graph = graph.compile(checkpointer=checkpointer)

# For LangGraph Platform (it provides its own checkpointer)
friday_graph_platform = graph.compile()
