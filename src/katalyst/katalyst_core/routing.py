from typing import Union
from langgraph.graph import END
from langchain_core.agents import AgentFinish
from katalyst.katalyst_core.state import KatalystState

__all__ = ["route_after_agent", "route_after_pointer", "route_after_replanner", "route_after_verification"]


def route_after_agent(state: KatalystState) -> Union[str, object]:
    """
    Route after executor completes.
    1) If state.error_message contains [GRAPH_RECURSION], go to "replanner".
    2) If agent completed the task (AgentFinish), go to "advance_pointer".
    3) Otherwise, something went wrong, go to "replanner".
    """
    if state.error_message and "[GRAPH_RECURSION]" in state.error_message:
        return "replanner"
    if isinstance(state.agent_outcome, AgentFinish):
        return "advance_pointer"
    # If no AgentFinish, something went wrong
    return "replanner"


def route_after_pointer(state: KatalystState) -> Union[str, object]:
    """
    1) If [REPLAN_REQUESTED] marker is present in state.error_message, go to "replanner".
    2) If plan exhausted (task_idx >= len(task_queue)), go to "replanner".
    3) Else if tasks remain, go to "executor".
    """
    if state.error_message and "[REPLAN_REQUESTED]" in state.error_message:
        return "replanner"
    if state.task_idx >= len(state.task_queue):
        return "replanner"
    return "executor"


def route_after_replanner(state: KatalystState) -> str:
    """
    Router for after the replanner node.
    - If replanner provided new tasks, route to human_plan_verification for approval.
    - If replanner provided no tasks, route to END (task complete).
    """
    if state.task_queue:  # If replanner provided new tasks
        return "human_plan_verification"  # Need human approval for new plan
    else:  # No tasks means we're done
        return END


def route_after_verification(state: KatalystState) -> Union[str, object]:
    """
    Router for after human plan verification.
    - If user rejected with feedback (REPLAN_REQUESTED), route to planner.
    - If user approved (task_queue exists), route to executor.
    - If no task queue, route to END (user cancelled).
    """
    if state.error_message and "[REPLAN_REQUESTED]" in state.error_message:
        return "planner"  # User provided feedback, regenerate plan
    elif state.task_queue:  # User approved, proceed with plan
        return "executor"
    else:
        return END  # No tasks, user must have cancelled
