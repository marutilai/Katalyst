import os
from katalyst_agent.state import KatalystState
from katalyst_agent.services.llms import get_llm_instructor
from langchain_core.messages import AIMessage
from katalyst_agent.utils.models import SubtaskList
from katalyst_agent.utils.logger import get_logger


def planner(state: KatalystState) -> KatalystState:
    """
    Generate initial subtask list in state.task_queue, set state.task_idx = 0, etc.
    Uses Instructor to get a structured list of subtasks from the LLM.

    * Primary Task: Call an LLM to generate an initial, ordered list of sub-task descriptions based on the main state.task.
    * State Changes:
    * Sets state.task_queue to the new list of sub-task strings.
    * Resets state.task_idx = 0.
    * Resets state.outer_cycles = 0 (as this is the start of a new P-n-E attempt).
    * Resets state.completed_tasks = [].
    * Resets state.response = None.
    * Resets state.error_message = None.
    * Optionally, logs the generated plan to state.chat_history as an AIMessage or SystemMessage.
    * Returns: The updated KatalystState.
    """
    logger = get_logger()
    logger.info(f"[PLANNER] Starting planner node...")

    llm = get_llm_instructor()
    prompt = (
        "You are a helpful coding agent. "
        "Break down the following high-level task into a short, ordered list of concrete subtasks. "
        "Each subtask should be a single sentence, and the list should be exhaustive and in logical order.\n"
        f"Task: {state.task}\n"
        "Return the subtasks as a JSON list of strings."
    )    
    logger.info(f"[PLANNER] Prompt to LLM:\n{prompt}")
    # Call the LLM with Instructor and Pydantic response model
    response = llm.chat.completions.create(
        messages=[{"role": "system", "content": prompt}],
        response_model=SubtaskList,
        temperature=0.3,
    )
    logger.debug(f"[PLANNER] Raw LLM response: {response}")
    subtasks = response.subtasks
    logger.info(f"[PLANNER] Parsed subtasks: {subtasks}")
    
    # Update state
    state.task_queue = subtasks
    state.task_idx = 0
    state.outer_cycles = 0
    state.completed_tasks = []
    state.response = None
    state.error_message = None

    # Log the plan to chat_history
    state.chat_history.append(AIMessage(content=f"Generated plan:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(subtasks))))
    logger.info(f"[PLANNER] End of planner node.")
    return state