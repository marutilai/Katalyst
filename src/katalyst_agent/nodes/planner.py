import os
from katalyst_agent.state import KatalystState
from katalyst_agent.services.llms import get_llm_instructor
from langchain_core.messages import AIMessage
from katalyst_agent.utils.models import SubtaskList
from katalyst_agent.utils.logger import get_logger
from katalyst_agent.utils.tools import extract_tool_descriptions


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
    logger.debug(f"[PLANNER] Starting planner node...")

    llm = get_llm_instructor()
    tool_descriptions = extract_tool_descriptions()
    tool_list_str = "\n".join(f"- {name}: {desc}" for name, desc in tool_descriptions)

    # Modular prompt sections
    context_section = (
        "# CONTEXT\n"
        "You are a planning assistant for a ReAct agent. Your job is to break down the user's high-level goal into a logical sequence of actionable subtasks.\n"
        "The ReAct agent can execute specific actions using a set of tools.\n"
        "When you generate subtasks, try to make them clearly actionable by one of these tools if appropriate.\n"
    )
    tools_section = (
        "# TOOLS AVAILABLE\n"
        f"{tool_list_str}\n"
    )
    instructions_section = (
        "# INSTRUCTIONS\n"
        "When generating subtasks, if a specific tool is clearly the best fit, you can phrase the subtask like:\n"
        "'Use the <tool_name> tool to ...' OR 'Determine ...' (and the ReAct agent will pick the right tool).\n"
        "Your primary goal is to create a logical sequence of steps (subtasks).\n"
    )
    task_section = (
        "# TASK\n"
        f"{state.task}\n"
    )
    output_format_section = (
        "# OUTPUT FORMAT\n"
        "Break down the above high-level task into a short, ordered list of concrete subtasks.\n"
        "Each subtask should be a single sentence, and the list should be exhaustive and in logical order.\n"
        "Return the subtasks as a JSON list of strings.\n"
    )

    prompt = "\n\n".join([
        context_section,
        tools_section,
        instructions_section,
        task_section,
        output_format_section
    ])
    logger.debug(f"[PLANNER] Prompt to LLM:\n{prompt}")
    # Call the LLM with Instructor and Pydantic response model
    response = llm.chat.completions.create(
        messages=[{"role": "system", "content": prompt}],
        response_model=SubtaskList,
        temperature=0.3,
    )
    logger.debug(f"[PLANNER] Raw LLM response: {response}")
    subtasks = response.subtasks
    logger.debug(f"[PLANNER] Parsed subtasks: {subtasks}")
    
    # Update state
    state.task_queue = subtasks
    state.task_idx = 0
    state.outer_cycles = 0
    state.completed_tasks = []
    state.response = None
    state.error_message = None

    # Log the plan to chat_history
    state.chat_history.append(AIMessage(content=f"Generated plan:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(subtasks))))
    logger.debug(f"[PLANNER] End of planner node.")
    return state