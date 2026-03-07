"""LangGraph entrypoint — adds app/ to sys.path so bare imports work,
then patches relative imports to absolute before loading the graph."""
import importlib
import sys
from pathlib import Path

# Add app/ to sys.path so bare imports like `from config import settings` resolve
_app_dir = str(Path(__file__).parent / "app")
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

# Also ensure backend/ is on the path for `app.agent.*` style imports
_backend_dir = str(Path(__file__).parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# Pre-load the agent package so relative imports work
import app.agent  # noqa: E402

# Now import the graph — the relative imports inside graph.py will resolve
# because app.agent is a loaded package
from app.agent.graph import friday_graph_platform as friday_graph  # noqa: E402

__all__ = ["friday_graph"]
