from katalyst_agent.state import KatalystState
from katalyst_agent.utils.logger import get_logger
from langchain_core.agents import AgentFinish

def advance_pointer(state: KatalystState) -> KatalystState:
    """
    1) Called when AgentFinish → log completed subtask & summary.
    2) Increment state.task_idx, reset state.inner_cycles & state.action_trace.
    3) If the new plan is exhausted, bump outer_cycles and maybe set state.response.
    4) Return state.

    * Primary Task: Finalize the completed sub-task, advance to the next sub-task in the queue, and perform outer loop checks.
    * State Changes:
    * Retrieves the final_answer_string from state.agent_outcome.return_values["output"].
    * Appends (state.task_queue[state.task_idx], final_answer_string) to state.completed_tasks.
    * Increments state.task_idx += 1.
    * Resets state.inner_cycles = 0.
    * Clears state.action_trace = [].
    * Clears state.agent_outcome = None.
    * Clears state.error_message = None (as the sub-task successfully finished, clearing any prior ReAct loop errors for that sub-task).
    * Checks if the plan is now exhausted: if state.task_idx >= len(state.task_queue):
    * If true, increments state.outer_cycles += 1.
    * Checks if state.outer_cycles > state.max_outer_cycles:
    * If true, sets state.response to an error message (e.g., "Outer loop limit exceeded...").
    * Returns: The updated KatalystState.    
    """
    logger = get_logger()
    logger.debug("[ADVANCE_POINTER] Starting advance_pointer node...")

    # 1) Log completion: get the subtask and summary from agent_outcome
    if isinstance(state.agent_outcome, AgentFinish):
        try:
            current_subtask = state.task_queue[state.task_idx]
        except IndexError:
            current_subtask = "[UNKNOWN_SUBTASK]"
        summary = state.agent_outcome.return_values.get("output", "[NO_OUTPUT]")
        state.completed_tasks.append((current_subtask, summary))
        logger.info(f"[ADVANCE_POINTER] Completed subtask: {current_subtask} | Summary: {summary}")
    else:
        logger.warning("[ADVANCE_POINTER] [Warning] Called without AgentFinish; skipping subtask logging.")

    # 2) Move to next subtask and reset loop state
    state.task_idx += 1
    state.inner_cycles = 0
    state.action_trace.clear()
    state.agent_outcome = None
    state.error_message = None

    # 3) If plan is exhausted, check outer-loop guard
    if state.task_idx >= len(state.task_queue):
        state.outer_cycles += 1
        logger.debug(f"[ADVANCE_POINTER] Plan exhausted. Incremented outer_cycles to {state.outer_cycles}.")
        if state.outer_cycles > state.max_outer_cycles:
            state.response = (
                f"Stopped: outer loop exceeded {state.max_outer_cycles} cycles."
            )
            logger.info(f"[ADVANCE_POINTER] Outer loop limit exceeded. Setting response and terminating.")

    logger.debug("[ADVANCE_POINTER] End of advance_pointer node.")
    return state