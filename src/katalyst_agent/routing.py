from typing import Union
from langgraph.graph import END
from langchain_core.agents import AgentAction
from katalyst_agent.state import KatalystState

__all__ = ["route_after_agent", "route_after_pointer"]

def route_after_agent(state: KatalystState) -> Union[str, object]:
    """
    1) If state.response is already set (inner guard tripped), return END.
    2) Else if the last LLM outcome was AgentAction, go to "tool_runner".
    3) Else (AgentFinish), go to "advance_pointer".
    """
    if state.response: # inner guard tripped
        return END
    return "tool_runner" if isinstance(state.agent_outcome, AgentAction) else "advance_pointer"


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