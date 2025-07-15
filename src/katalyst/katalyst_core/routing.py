"""
Simplified routing for single-node agent architecture.
"""
from typing import Union
from langgraph.graph import END
from katalyst.katalyst_core.state import KatalystState

__all__ = ["route_agent"]


def route_agent(state: KatalystState) -> Union[str, object]:
    """
    Simple routing for the agent node.
    - If completion_status is set (completed, error, or max_cycles), route to END
    - Otherwise, continue to agent_react for another cycle
    """
    if state.completion_status:
        return END
    return "agent_react"