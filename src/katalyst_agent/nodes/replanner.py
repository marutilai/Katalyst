from katalyst_agent.state import KatalystState
from katalyst_agent.services.llms import get_llm_instructor
from katalyst_agent.utils.models import SubtaskList
from langchain_core.messages import AIMessage
from katalyst_agent.utils.logger import get_logger

def replanner(state: KatalystState) -> KatalystState:
    """
    1) If final answer is ready (state.response already set), do nothing.
    2) Otherwise, generate a fresh plan into state.task_queue & reset state.task_idx = 0.
    3) Return state.

    * Primary Task: Review progress and decide if the overall task is complete or if a new/modified plan is needed.
    * State Changes:
    * If the overall task is deemed complete:
    * Sets state.response to the final answer/summary for the user.
    * Optionally, clears state.task_queue or sets it to [].
    * If the overall task is NOT complete (or a previous plan failed/was insufficient):
    * Calls an LLM to generate a new list of sub-task descriptions based on the original task, what's been completed (state.completed_tasks), and why re-planning is occurring (e.g., initial plan exhausted, or a previous step indicated a need for plan change).
    * Sets state.task_queue to this new list.
    * Resets state.task_idx = 0.
    * Clears state.response = None (to ensure the new plan starts executing).
    * Logs its decision/new plan to state.chat_history.
    * Returns: The updated KatalystState.    
    """
    logger = get_logger()
    logger.info("[REPLANNER] Starting replanner node...")

    if state.response:
        logger.info("[REPLANNER] Final answer already set. No replanning needed.")
        return state

    llm = get_llm_instructor()
    completed_str = "\n".join(f"- {task}: {summary}" for task, summary in state.completed_tasks) or "None yet."
    prompt = (
        "You are a helpful coding agent. The original task is: "
        f"{state.task}\n"
        "Here are the subtasks you've already completed (with summaries):\n"
        f"{completed_str}\n"
        "The previous plan was exhausted or a replanning event was triggered. "
        "Please generate a new, logically ordered list of concrete subtasks to finish the overall task. "
        "Return the subtasks as a JSON list of strings."
    )
    logger.info(f"[REPLANNER] Prompt to LLM:\n{prompt}")
    response = llm.chat.completions.create(
        messages=[{"role": "system", "content": prompt}],
        response_model=SubtaskList,
        temperature=0.3,
    )
    logger.debug(f"[REPLANNER] Raw LLM response: {response}")
    subtasks = response.subtasks
    logger.info(f"[REPLANNER] Parsed new subtasks: {subtasks}")

    state.task_queue = subtasks
    state.task_idx = 0
    state.response = None
    state.error_message = None

    state.chat_history.append(AIMessage(content=f"[REPLANNER] Generated new plan:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(subtasks))))
    logger.info("[REPLANNER] End of replanner node.")
    return state