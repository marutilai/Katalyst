from typing import Union
from langgraph.graph import END
from langchain_core.agents import AgentFinish
from katalyst.katalyst_core.state import KatalystState

__all__ = ["route_after_agent", "route_after_pointer", "route_after_replanner", "route_after_verification"]


def route_after_agent(state: KatalystState) -> Union[str, object]:
    """
    Route after agent_react completes.
    1) If state.response is already set, return END.
    2) If state.error_message contains [GRAPH_RECURSION], go to "replanner".
    3) If agent completed the task (AgentFinish), go to "advance_pointer".
    4) Otherwise, something went wrong, go to "replanner".
    """
    if state.response:  # final response set
        return END
    if state.error_message and "[GRAPH_RECURSION]" in state.error_message:
        return "replanner"
    if isinstance(state.agent_outcome, AgentFinish):
        return "advance_pointer"
    # If no AgentFinish, something went wrong
    return "replanner"


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
    - If replanner provided new tasks, route to human_plan_verification for approval.
    - If replanner provided no tasks and no response, set a generic completion response and route to END.
    """
    if state.response:  # If replanner set a final response (e.g. task done)
        return END
    elif state.task_queue:  # If replanner provided new tasks
        return "human_plan_verification"  # Need human approval for new plan
    else:  # No tasks and no response (should not happen, but handle gracefully)
        if not state.response:
            state.response = "Overall task concluded after replanning resulted in an empty task queue."
        return END


def route_after_verification(state: KatalystState) -> Union[str, object]:
    """
    Router for after human plan verification.
    - If user cancelled (response is set), route to END.
    - If user rejected with feedback (REPLAN_REQUESTED), route to planner.
    - If user approved (task_queue exists), route to agent_react.
    """
    if state.response:  # User cancelled
        return END
    elif state.error_message and "[REPLAN_REQUESTED]" in state.error_message:
        return "planner"  # User provided feedback, regenerate plan
    elif state.task_queue:  # User approved, proceed with plan
        return "agent_react"
    else:
        return END  # Safety fallback
