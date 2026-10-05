from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent

from repair_agent.model import get_model
from repair_agent.tools import TOOLS


def build_graph() -> CompiledStateGraph:
    return create_react_agent(get_model(), TOOLS)
