from src.katalyst_core.state import KatalystState
from src.katalyst_core.services.llms import (
    get_llm_instructor,
    get_llm_fallbacks,
    get_llm_timeout,
)
from src.katalyst_core.utils.models import (
    ReplannerOutput,
)
from langchain_core.messages import AIMessage
from src.katalyst_core.utils.logger import get_logger
from src.katalyst_core.utils.error_handling import (
    ErrorType,
    create_error_message,
    classify_error,
    format_error_for_llm,
)
import os


def replanner(state: KatalystState) -> KatalystState:
    """
    1) If a final response is already set (e.g., by a guardrail in advance_pointer), do nothing.
    2) Otherwise, call an LLM to analyze progress and either:
       a) Determine the overall goal is complete, then set state.response with a summary.
       b) Generate a new plan of subtasks if the goal is not yet achieved.
    3) Update state accordingly (task_queue, task_idx, response, chat_history).
    """
    logger = get_logger()
    logger.debug(
        f"[REPLANNER] Starting replanner node. Current task_idx: {state.task_idx}, task_queue length: {len(state.task_queue)}"
    )

    # If a response is already set (e.g., by max_outer_cycles in advance_pointer),
    # it means the process should terminate. Don't replan.
    if state.response:
        logger.debug(
            f"[REPLANNER] Final response already set in state: '{state.response}'. No replanning needed. Routing to END."
        )
        # Ensure task_queue is empty so route_after_replanner goes to END
        state.task_queue = []
        return state

    llm = get_llm_instructor()
    completed_tasks_str = (
        "\n".join(
            f"- '{task_desc}': {summary}"
            for task_desc, summary in state.completed_tasks
        )
        if state.completed_tasks
        else "No sub-tasks have been completed yet."
    )

    prompt = f"""
        # REPLANNER ROLE
        You are an intelligent planning assistant responsible for analyzing progress and determining the next steps. 
        Your role is to either confirm task completion or generate a new plan of subtasks to achieve the remaining goals.

        # TASK ANALYSIS
        ORIGINAL GOAL: {state.task}

        COMPLETED SUBTASKS & THEIR OUTCOMES (most recent first):
        {completed_tasks_str}

        # DECISION GUIDELINES
        1. Carefully review the ORIGINAL GOAL and COMPLETED SUBTASKS.
        2. Determine if the ORIGINAL GOAL has been fully achieved by considering:
           - All required information has been gathered
           - All necessary files have been created/modified
           - All user interactions have been completed
           - All validation steps have been performed
        3. If the goal is complete, return is_complete: true and an empty subtasks list: {{"subtasks": []}}
        4. If the goal is NOT complete, return is_complete: false and a new subtasks list.
           - Focuses on remaining tasks only
           - Avoids repeating completed tasks
           - Addresses any failed or incomplete tasks
           - Maintains logical task ordering

        # SUBTASK GENERATION RULES
        When creating new subtasks:
        1. Each subtask must be a single, actionable step
        2. Use clear, tool-specific language (e.g., 'Use read_file to...')
        3. Include necessary parameters in the description
        4. Order tasks logically (e.g., read before write)
        5. Handle dependencies appropriately

        # ERROR RECOVERY
        If previous tasks failed or were incomplete:
        1. Analyze why the previous attempt failed
        2. Propose a different approach
        3. Add validation steps to confirm success
        4. Consider asking for user guidance if needed

        # OUTPUT FORMAT
        Return a JSON object with two keys: 'is_complete' (boolean) and 'subtasks' (list of strings).
        Example: {{"is_complete": true, "subtasks": []}} or {{"is_complete": false, "subtasks": ["task1", "task2"]}}

        # COMPLETION CHECKLIST
        Before returning is_complete: true, verify:
        1. All required information is available
        2. All necessary files exist with correct content
        3. All user interactions are complete
        4. No pending tasks remain
        5. No errors need to be addressed

        CURRENT SITUATION: The previous plan is exhausted or a replanning event was triggered. 
        Analyze the progress and provide your JSON response.
    """
    logger.debug(f"[REPLANNER] Prompt to LLM:\n{prompt}")

    try:
        fallbacks = get_llm_fallbacks()
        timeout = get_llm_timeout()
        llm_response_model = llm.chat.completions.create(
            messages=[{"role": "system", "content": prompt}],
            response_model=ReplannerOutput,  # Expects {"is_complete": bool, "subtasks": [...]}
            temperature=0.1,
            # Instructor's retries for Pydantic validation (if LLM output doesn't fit model)
            max_retries=2,
            # LiteLLM's native retries for API call failures
            num_retries=2,
            model=os.getenv("KATALYST_LITELLM_MODEL", "gpt-4.1"),
            fallbacks=fallbacks if fallbacks else None,
            timeout=timeout,
        )
        # Check if the model used is the same as the one configured or a fallback was used
        actual_model = getattr(llm_response_model, "model", None)
        if actual_model and actual_model != os.getenv(
            "KATALYST_LITELLM_MODEL", "gpt-4.1"
        ):
            logger.info(f"[LLM] Fallback model used: {actual_model}")

        logger.debug(
            f"[REPLANNER] Raw LLM response from instructor: {llm_response_model}"
        )

        is_complete = llm_response_model.is_complete
        new_subtasks = llm_response_model.subtasks
        logger.info(
            f"[REPLANNER] LLM replanner output: is_complete={is_complete}, subtasks={new_subtasks}"
        )

        if is_complete or not new_subtasks:
            logger.info(
                "[REPLANNER] LLM indicated original goal is complete (is_complete=True) or no new subtasks are needed."
            )
            state.task_queue = []  # Ensure task queue is empty for routing to END
            state.task_idx = 0  # Reset index

            # Construct a final response message based on completed tasks
            if state.completed_tasks:
                final_summary_of_work = (
                    "Katalyst has completed the following sub-tasks based on the plan:\n"
                    + "\n".join(
                        [f"- '{desc}': {summ}" for desc, summ in state.completed_tasks]
                    )
                    + "\n\nThe overall goal appears to be achieved."
                )
                state.response = final_summary_of_work
            else:
                # This case should be rare if a planner ran, but handle it.
                state.response = "The task was concluded without any specific sub-tasks being completed according to the plan."

            state.chat_history.append(
                AIMessage(
                    content=f"[REPLANNER] Goal achieved. Final response: {state.response}"
                )
            )
            logger.debug(
                f"[REPLANNER] Goal achieved. Setting final response. Task queue empty."
            )

        else:  # LLM provided new subtasks
            logger.info(
                f"[REPLANNER] Generated new plan with {len(new_subtasks)} subtasks."
            )
            state.task_queue = new_subtasks
            state.task_idx = 0  # Reset task index for the new plan
            state.response = (
                None  # Clear any previous overall response, as we have a new plan
            )
            state.error_message = None  # Clear any errors that led to replanning
            state.inner_cycles = 0  # Reset inner cycles for the new plan's first task
            state.action_trace = []  # Clear action trace for the new plan's first task
            # Outer cycles are managed by advance_pointer when a plan is exhausted

            state.chat_history.append(
                AIMessage(
                    content=f"[REPLANNER] Generated new plan:\n"
                    + "\n".join(f"{i+1}. {s}" for i, s in enumerate(new_subtasks))
                )
            )
            logger.debug(
                f"[REPLANNER] New plan set. Task queue size: {len(state.task_queue)}, Task index: {state.task_idx}"
            )

    except Exception as e:
        error_msg = create_error_message(
            ErrorType.LLM_ERROR, f"Failed to generate new plan: {str(e)}", "REPLANNER"
        )
        logger.error(f"[REPLANNER] {error_msg}")
        state.error_message = error_msg
        state.response = "Failed to generate new plan. Please try again."

    logger.debug(
        f"[REPLANNER] End of replanner node. state.response: '{state.response}', task_queue: {state.task_queue}"
    )
    return state
