from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.logger import get_logger
from langchain_core.agents import AgentFinish
from katalyst.katalyst_core.utils.error_handling import (
    ErrorType,
    create_error_message,
    classify_error,
    format_error_for_llm,
)
from katalyst.katalyst_core.utils.task_display import get_task_progress_display


def _display_task_progress(state: KatalystState, logger) -> None:
    """Display visual progress of all tasks in the queue."""
    progress_display = get_task_progress_display(state)
    logger.info(progress_display)


def advance_pointer(state: KatalystState) -> KatalystState:
    """
    Called when agent_react completes a task with AgentFinish.
    
    1) Log completed subtask & summary
    2) Increment state.task_idx
    3) Clear agent_outcome and error_message
    4) Check if plan is exhausted and handle outer loop limits
    
    Returns: The updated KatalystState
    """
    logger = get_logger()

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
        
        # Display visual task progress
        _display_task_progress(state, logger)
    else:
        error_msg = create_error_message(
            ErrorType.PARSING_ERROR,
            "Called without AgentFinish; skipping subtask logging.",
            "ADVANCE_POINTER",
        )
        logger.warning(f"[ADVANCE_POINTER] {error_msg}")

    # 2) Move to next subtask
    state.task_idx += 1
    state.agent_outcome = None
    state.error_message = None
    
    # Check if we're moving to a new planner task (not a subtask)
    if state.original_plan and state.task_idx < len(state.task_queue):
        current_task = state.task_queue[state.task_idx]
        # If this task is in the original plan, it's a new planner task
        if current_task in state.original_plan:
            # MINIMAL: operation_context is commented out
            # # Log operation context before clearing
            # context_before = state.operation_context.get_context_for_agent()
            # if context_before:
            #     logger.debug(f"[ADVANCE_POINTER] Operation context before clearing:\n{context_before}")
            # 
            # # Clear operation context for new planner task
            # state.operation_context.clear()
            # logger.info("[ADVANCE_POINTER] Cleared operation context for new planner task")
            pass
    
    # 3) If plan is exhausted, check outer-loop guard
    if state.task_idx >= len(state.task_queue):
        state.outer_cycles += 1
        if state.outer_cycles > state.max_outer_cycles:
            error_msg = create_error_message(
                ErrorType.LLM_ERROR,
                f"Outer loop exceeded {state.max_outer_cycles} cycles.",
                "ADVANCE_POINTER",
            )
            state.response = error_msg
            logger.warning(f"[ADVANCE_POINTER][GUARDRAIL] {error_msg}")

    return state
