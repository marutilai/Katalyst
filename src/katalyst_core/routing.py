from typing import Union
from langgraph.graph import END
from langchain_core.agents import AgentAction
from src.katalyst_core.state import KatalystState

__all__ = ["route_after_agent", "route_after_pointer", "route_after_replanner"]


def route_after_agent(state: KatalystState) -> Union[str, object]:
    """
    1) If state.response is already set (inner guard tripped), return END.
    2) If state.error_message contains [GRAPH_RECURSION], go to "replanner".
    3) Else if the last LLM outcome was AgentAction, go to "tool_runner".
    4) Else (AgentFinish), go to "advance_pointer".
    """
    if state.response:  # inner guard tripped
        return END
    if state.error_message and "[GRAPH_RECURSION]" in state.error_message:
        return "replanner"
    return (
        "tool_runner"
        if isinstance(state.agent_outcome, AgentAction)
        else "advance_pointer"
    )


def route_after_pointer(state: KatalystState) -> Union[str, object]:
    """
    1) If state.response is already set (outer guard tripped), return END.
    2) If [REPLAN_REQUESTED] marker is present in state.error_message, go to "replanner".
    3) If plan exhausted (task_idx >= len(task_queue)) and no response, go to "replanner".
    4) Else if tasks remain, go to "agent_react".
    """
    if state.response:  # outer guard tripped
        return END
    if state.error_message and "[REPLAN_REQUESTED]" in state.error_message:
        return "replanner"
    if state.task_idx >= len(state.task_queue):
        return "replanner"
    return "agent_react"


def route_after_replanner(state: KatalystState) -> str:
    """
    Router for after the replanner node.
    - If replanner set a final response (task done), route to END.
    - If replanner provided new tasks, route to agent_react.
    - If replanner provided no tasks and no response, set a generic completion response and route to END.
    """
    if state.response:  # If replanner set a final response (e.g. task done)
        return END
    elif state.task_queue:  # If replanner provided new tasks
        return "agent_react"
    else:  # No tasks and no response (should not happen, but handle gracefully)
        if not state.response:
            state.response = "Overall task concluded after replanning resulted in an empty task queue."
        return END
