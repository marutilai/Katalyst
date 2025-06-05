import os
from katalyst_agent.state import KatalystState
from katalyst_agent.services.llms import get_llm_instructor
from langchain_core.messages import AIMessage
from katalyst_agent.utils.models import SubtaskList
from katalyst_agent.utils.logger import get_logger
from katalyst_agent.utils.tools import extract_tool_descriptions
from katalyst_agent.utils.error_handling import (
    ErrorType,
    create_error_message,
    classify_error,
    format_error_for_llm,
)


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
    # Modular prompt sections
    context_section = (
        "# CONTEXT\n"
        "You are an expert planning assistant for a ReAct-style AI agent. Your primary responsibility is to break down a high-level user GOAL into a sequence of concrete, actionable, and logically ordered sub-tasks. Each sub-task will be executed by a ReAct agent that can use a specific set of tools."
    )

    available_tools_section = (
        "# AVAILABLE TOOLS FOR THE ReAct AGENT\n"
        "The ReAct agent that will execute your sub-tasks has access to the following tools. Understand their capabilities to create effective sub-tasks:\n"
        f"{tool_list_str}\n"  # Use the concise list here
        "NOTE: The ReAct agent does NOT have a 'navigate' or 'change directory' tool. All file operations must use tools that accept full or relative paths (e.g., 'list_files', 'read_file', 'write_to_file' with a 'path' argument)."
    )

    subtask_guidelines_section = (
        "# SUB-TASK GENERATION GUIDELINES\n"
        "1.  **Action-Oriented:** Each sub-task should describe a clear action to be performed. If the action involves interacting with the file system, user, or executing commands, it will likely map to a tool call by the ReAct agent.\n"
        "2.  **Tool Implication:** Whenever possible, phrase sub-tasks so they clearly imply which of the available tools the ReAct agent should use. For example:\n"
        "    - Instead of: 'Determine the contents of config.json.'\n"
        "    - Prefer:     'Use the `read_file` tool to get the content of 'config.json'.'\n"
        "    - Instead of: 'Go to the src/utils directory and find all Python files.'\n"
        "    - Prefer:     'Use the `list_files` tool to find all Python files in the 'src/utils' directory.' (The ReAct agent can then filter for .py)\n"
        "                  OR 'Use `search_files` with path 'src/utils' and file_pattern '*.py' to get Python files.'\n"
        "3.  **Parameter Inclusion (Implicit or Explicit):** If a sub-task implies a tool that needs specific parameters (like a path for `read_file`), try to include that necessary information directly in the sub-task description. The ReAct agent will extract it.\n"
        "    - Example: 'Create a new directory named `my_project_folder`.' (Implies `write_to_file` might be used with a placeholder, or a future `create_directory` tool. For now, `write_to_file` makes directories if path is given for a file within it.)\n"
        "    - Better: 'Create a placeholder file named `.gitkeep` inside a new directory `my_project_folder` using `write_to_file`.' (This directly uses an existing tool to achieve folder creation).\n"
        "4.  **User Interaction:** If information is needed from the user (filename, content, confirmation), the sub-task MUST be phrased to instruct the ReAct agent to use the `request_user_input` tool.\n"
        "    - Example: 'Use the `request_user_input` tool to ask the user for the desired project name, suggesting `new_project`.'\n"
        "5.  **Single, Concrete Step:** Each sub-task should represent a single, manageable step for the ReAct agent.\n"
        "6.  **Logical Order:** Sub-tasks must be in a sequence that makes sense for achieving the overall GOAL.\n"
        "7.  **Exhaustive (for the initial plan):** The initial plan should attempt to cover all necessary steps to reach the GOAL.\n"
        "8.  **Avoid Abstract Actions:** Do not create subtasks like 'Navigate to directory X' or 'Understand the file structure'. Instead, create subtasks that use tools to achieve these underlying goals, e.g., 'Use `list_files` on directory X to understand its structure.'"
    )

    goal_section = "# HIGH-LEVEL USER GOAL\n" f"{state.task}\n"

    output_format_section = (
        "# OUTPUT FORMAT\n"
        'Based on the GOAL, the AVAILABLE TOOLS, and the SUB-TASK GENERATION GUIDELINES, provide your response as a JSON object with a single key "subtasks". The value should be a list of strings, where each string is a sub-task description.\n'
        'Example JSON output: {"subtasks": ["Use the `list_files` tool to list contents of the current directory.", "Use the `request_user_input` tool to ask the user which file they want to read from the list."]}'
    )

    prompt = "\n\n".join(
        [
            context_section,
            available_tools_section,
            subtask_guidelines_section,
            goal_section,
            output_format_section,
        ]
    )
    logger.debug(f"[PLANNER] Prompt to LLM:\n{prompt}")

    try:
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
        plan_message = f"Generated plan:\n" + "\n".join(
            f"{i+1}. {s}" for i, s in enumerate(subtasks)
        )
        state.chat_history.append(AIMessage(content=plan_message))
        logger.info(f"[PLANNER] {plan_message}")

    except Exception as e:
        error_msg = create_error_message(
            ErrorType.LLM_ERROR, f"Failed to generate plan: {str(e)}", "PLANNER"
        )
        logger.error(f"[PLANNER] {error_msg}")
        state.error_message = error_msg
        state.response = "Failed to generate initial plan. Please try again."

    logger.debug(f"[PLANNER] End of planner node.")
    return state
