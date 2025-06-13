from src.katalyst_core.state import KatalystState
from src.katalyst_core.utils.logger import get_logger
from langchain_core.agents import AgentFinish
from src.katalyst_core.utils.error_handling import (
    ErrorType,
    create_error_message,
    classify_error,
    format_error_for_llm,
)


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
            error_msg = create_error_message(
                ErrorType.PARSING_ERROR,
                "Could not find current subtask in task queue.",
                "ADVANCE_POINTER",
            )
            logger.warning(f"[ADVANCE_POINTER] {error_msg}")

        summary = state.agent_outcome.return_values.get("output", "[NO_OUTPUT]")
        state.completed_tasks.append((current_subtask, summary))
        logger.info(
            f"[ADVANCE_POINTER] Completed subtask: {current_subtask} | Summary: {summary}"
        )
    else:
        error_msg = create_error_message(
            ErrorType.PARSING_ERROR,
            "Called without AgentFinish; skipping subtask logging.",
            "ADVANCE_POINTER",
        )
        logger.warning(f"[ADVANCE_POINTER] {error_msg}")

    # 2) Move to next subtask and reset loop state
    state.task_idx += 1
    state.inner_cycles = 0
    state.action_trace.clear()
    state.agent_outcome = None
    state.error_message = None

    # 3) If plan is exhausted, check outer-loop guard
    if state.task_idx >= len(state.task_queue):
        state.outer_cycles += 1
        logger.debug(
            f"[ADVANCE_POINTER] Plan exhausted. Incremented outer_cycles to {state.outer_cycles}."
        )
        if state.outer_cycles > state.max_outer_cycles:
            error_msg = create_error_message(
                ErrorType.LLM_ERROR,
                f"Outer loop exceeded {state.max_outer_cycles} cycles.",
                "ADVANCE_POINTER",
            )
            state.response = error_msg
            logger.warning(f"[ADVANCE_POINTER][GUARDRAIL] {error_msg}")

    logger.debug("[ADVANCE_POINTER] End of advance_pointer node.")
    return state
