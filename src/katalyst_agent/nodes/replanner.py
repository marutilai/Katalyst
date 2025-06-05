from katalyst_agent.state import KatalystState
from katalyst_agent.services.llms import get_llm_instructor
from katalyst_agent.utils.models import SubtaskList
from langchain_core.messages import AIMessage
from katalyst_agent.utils.logger import get_logger
from katalyst_agent.utils.error_handling import (
    ErrorType,
    create_error_message,
    classify_error,
    format_error_for_llm,
)


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

    prompt = (
        "You are an intelligent planning assistant. Your role is to analyze the progress towards an overall goal and, if necessary, create a new plan of subtasks.\n\n"
        f"ORIGINAL GOAL: {state.task}\n\n"
        "COMPLETED SUBTASKS & THEIR OUTCOMES (most recent first for context):\n"
        f"{completed_tasks_str}\n\n"  # Display completed tasks
        "INSTRUCTIONS:\n"
        "1. Carefully review the ORIGINAL GOAL and the COMPLETED SUBTASKS & THEIR OUTCOMES.\n"
        "2. Determine if the ORIGINAL GOAL has been fully achieved. Consider the summaries of completed subtasks carefully. "
        "   If a subtask was to gather information (e.g., 'Ask user for filename') and its summary is just the question itself, that information was NOT gathered.\n"
        "3. If the ORIGINAL GOAL is fully achieved, you MUST return an empty list for 'subtasks': {\"subtasks\": []}.\n"
        "4. If the ORIGINAL GOAL is NOT YET achieved, generate a NEW, logically ordered list of concrete subtask descriptions required to fully achieve the remaining parts of the ORIGINAL GOAL. Each subtask should be a single, actionable sentence.\n"
        "   - Focus on the *next actionable steps*.\n"
        "   - Avoid re-listing subtasks whose outcomes indicate they have already effectively contributed to the goal, UNLESS a previous attempt clearly failed (e.g., user cancelled, error occurred) and a *different approach or re-attempt* is needed.\n"
        "   - If information gathering subtasks (like asking the user) were marked complete but their summary indicates the information wasn't actually obtained, you MUST re-issue those subtasks, possibly with more specific instructions for the agent executing them.\n"
        '5. Return your response as a JSON object with a single key "subtasks" containing a list of strings (the new subtask descriptions). Example: {"subtasks": ["New subtask 1 description.", "New subtask 2 description."]}\n\n'
        "6. If you are unsure, confused, or cannot determine the next step with confidence, you MUST add a subtask that uses the 'request_user_input' tool to ask the user for clarification or guidance. Do not guess or proceed without user input in such cases.\n"
        "CURRENT SITUATION: The previous plan of subtasks is now exhausted, or a specific replanning event (like a tool requesting it or an unrecoverable error) was triggered. Analyze the progress and provide your JSON response."
    )
    logger.debug(f"[REPLANNER] Prompt to LLM:\n{prompt}")

    try:
        # Call LLM to get new subtasks or an empty list if complete
        llm_response_model = llm.chat.completions.create(
            messages=[{"role": "system", "content": prompt}],
            response_model=SubtaskList,  # Expects {"subtasks": ["task1", "task2", ...]}
            temperature=0.3,  # Lower temperature for more deterministic planning
            max_retries=2,  # Add retries for instructor
        )
        logger.debug(
            f"[REPLANNER] Raw LLM response from instructor: {llm_response_model}"
        )

        new_subtasks = llm_response_model.subtasks
        logger.info(
            f"[REPLANNER] LLM proposed new subtasks: {new_subtasks if new_subtasks else 'None (goal likely complete)'}"
        )

        if (
            not new_subtasks
        ):  # LLM returns an empty list, signaling overall task completion
            logger.info(
                "[REPLANNER] LLM indicated original goal is complete (returned empty subtask list)."
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
