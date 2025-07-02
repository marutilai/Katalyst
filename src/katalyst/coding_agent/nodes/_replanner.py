from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.services.llms import (
    get_llm_client,
    get_llm_params,
)
from katalyst.katalyst_core.utils.models import (
    ReplannerOutput,
)
from langchain_core.messages import AIMessage
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import extract_tool_descriptions
from katalyst.katalyst_core.utils.error_handling import (
    ErrorType,
    create_error_message,
    classify_error,
    format_error_for_llm,
)
from katalyst.katalyst_core.utils.decorators import compress_chat_history
import os


@compress_chat_history()
def replanner(state: KatalystState) -> KatalystState:
    """
    Critiques the original plan based on execution history, determines if the
    overall goal is complete, and if not, generates a new, corrected plan.

    This node is the critical checkpoint in the agent's outer loop. It serves
    two purposes:
    1.  **Completion Judgement**: It first makes a holistic assessment to see if
        the user's overall goal has been met by analyzing the completed tasks.
    2.  **Corrective Replanning**: If the goal is not met, it analyzes why the
        previous plan failed or stalled and generates a new, more intelligent
        plan to get the agent back on track.
    """
    logger = get_logger()
    logger.debug("[REPLANNER] Starting replanner node...")

    if state.response:
        logger.debug("[REPLANNER] Final response already set. Skipping replanning.")
        state.task_queue = []
        return state

    # 1. Gather all context for the replanning prompt
    # =================================================
    # Use simplified API
    llm = get_llm_client("replanner", async_mode=False, use_instructor=True)
    llm_params = get_llm_params("replanner")
    tool_descriptions = extract_tool_descriptions()
    tool_list_str = "\n".join(f"- {name}: {desc}" for name, desc in tool_descriptions)

    original_plan_str = (
        "\n".join(f"{i+1}. {s}" for i, s in enumerate(state.original_plan))
        if state.original_plan
        else "No original plan was provided."
    )

    completed_tasks_str = (
        "\n".join(f"- '{task}': {summary}" for task, summary in state.completed_tasks)
        if state.completed_tasks
        else "No sub-tasks have been completed yet."
    )

    failed_task_trace_str = (
        "\n".join(
            f"Action: {action.tool}({action.tool_input})\nObservation: {obs}"
            for action, obs in state.action_trace
        )
        if state.action_trace
        else "No actions were taken for the current task."
    )

    current_task_str = (
        state.task_queue[state.task_idx]
        if state.task_idx < len(state.task_queue)
        else "No current task."
    )

    # 2. Construct the new, dual-purpose prompt
    # =================================================
    prompt = f"""
# ROLE & CONTEXT
You are a 'Replanner' for an AI agent. You have two critical responsibilities:
1.  **Completion Judgement:** First, you must rigorously determine if the user's Original Goal has been fully and satisfactorily achieved based on the evidence.
2.  **Corrective Replanning:** If, and ONLY IF, the goal is NOT complete, you must analyze the execution history, learn from mistakes, and create a new, improved plan.

# ANALYSIS SECTION
Carefully review the following information to make your decision.

## 1. The Original User Goal
This is the ultimate objective.
"{state.task}"

## 2. The Original Plan
This was the initial strategy.
{original_plan_str}

## 3. Successfully Completed Tasks
These tasks are DONE.
{completed_tasks_str}

## 4. The Current Task & Execution Trace
This is the task that was being executed, which may have failed or completed the plan.
- **Current Task:** "{current_task_str}"
- **Execution Trace:**
{failed_task_trace_str}

# AVAILABLE TOOLS
Your new plan must be grounded in the available tools.
{tool_list_str}

# INSTRUCTIONS

## STEP 1: MAKE A COMPLETION VERDICT
Based on all the information in the ANALYSIS SECTION, is the Original User Goal complete?
- To be complete, all required files must be created/modified, all information gathered, and all user requests satisfied.
- Do NOT assume completion just because all tasks in the original plan were attempted. The *outcome* is what matters.
- **If the goal is complete**, set `is_complete: true` in your JSON output. The `subtasks` list should be empty.
- **If the goal is NOT complete**, set `is_complete: false` and proceed to STEP 2.

## STEP 2: CREATE A CORRECTIVE REPLAN (ONLY if goal is not complete)
If you determined the goal is not complete, create a new plan to finish the work.
- **Learn from Mistakes:** Analyze the execution trace. If a tool failed, why? Was it a syntax error? A wrong path? Your new plan must address this.
- **Acknowledge Success:** Do not re-do tasks that were already completed successfully.
- **Be Specific & Actionable:** Each step must be a clear, executable action using the available tools.
- Your new plan should be a list of strings in the `subtasks` field of your JSON output.

# OUTPUT FORMAT
You MUST return a JSON object with two keys: `is_complete` (boolean) and `subtasks` (a list of strings for the new plan).
- **On success:** {{"is_complete": true, "subtasks": []}}
- **On failure/incomplete:** {{"is_complete": false, "subtasks": ["Use `read_file` to check 'config.json'.", "Use `request_user_input` to ask for the correct API key." ]}}
"""
    logger.debug(f"[REPLANNER] Prompt to LLM:\n{prompt}")

    # 3. Execute LLM call and update state
    # =================================================
    try:
        llm_response_model = llm.chat.completions.create(
            messages=[{"role": "system", "content": prompt}],
            response_model=ReplannerOutput,
            temperature=0.1,
            max_retries=2,
            num_retries=2,
            model=llm_params["model"],
            fallbacks=llm_params["fallbacks"] if llm_params["fallbacks"] else None,
            timeout=llm_params["timeout"],
        )

        actual_model = getattr(llm_response_model, "model", None)
        if actual_model and actual_model != llm_params["model"]:
            logger.info(f"[LLM] Fallback model used: {actual_model}")

        logger.debug(
            f"[REPLANNER] Raw LLM response from instructor: {llm_response_model}"
        )

        is_complete = llm_response_model.is_complete
        new_subtasks = llm_response_model.subtasks
        logger.debug(
            f"[REPLANNER] LLM replanner output: is_complete={is_complete}, subtasks={new_subtasks}"
        )

        if is_complete or not new_subtasks:
            logger.info(
                "[REPLANNER] LLM indicated original goal is complete or no new subtasks are needed."
            )
            state.task_queue = []
            state.task_idx = 0

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
                state.response = "The task was concluded without any specific sub-tasks being completed."

            state.chat_history.append(
                AIMessage(
                    content=f"[REPLANNER] Goal achieved. Final response: {state.response}"
                )
            )

        else:  # LLM provided new subtasks
            logger.info(
                f"[REPLANNER] Generated new plan with {len(new_subtasks)} subtasks."
            )
            # A new plan has been formulated; reset the relevant parts of the state.
            state.task_queue = new_subtasks
            state.task_idx = 0  # Start from the beginning of the new plan.
            state.response = None  # Clear any previous final response.
            state.error_message = None  # Clear the error that triggered the replan.
            state.inner_cycles = 0  # Reset the inner loop counter for the new task.
            state.action_trace = []  # Clear the action trace for the new task.

            state.chat_history.append(
                AIMessage(
                    content=f"[REPLANNER] Generated new plan:\n"
                    + "\n".join(f"{i+1}. {s}" for i, s in enumerate(new_subtasks))
                )
            )

    except Exception as e:
        error_msg = create_error_message(
            ErrorType.LLM_ERROR, f"Failed to generate new plan: {str(e)}", "REPLANNER"
        )
        logger.error(f"[REPLANNER] {error_msg}")
        state.error_message = error_msg
        state.response = "Failed to generate new plan. Please try again."

    logger.debug("[REPLANNER] End of replanner node.")
    return state
