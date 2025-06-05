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

    prompt = f"""
        # PLANNER ROLE
        You are an expert planning assistant for a ReAct-style AI agent. Your primary responsibility is to break down a high-level user GOAL into a sequence of concrete, actionable, and logically ordered sub-tasks. Each sub-task will be executed by a ReAct agent that can use a specific set of tools.

        # AVAILABLE TOOLS
        The ReAct agent that will execute your sub-tasks has access to the following tools. Understand their capabilities to create effective sub-tasks:
        {tool_list_str}

        NOTE: The ReAct agent does NOT have a 'navigate' or 'change directory' tool. All file operations must use tools that accept full or relative paths (e.g., 'list_files', 'read_file', 'write_to_file' with a 'path' argument).

        # SUBTASK GENERATION GUIDELINES
        1. Action-Oriented:
           - Each sub-task should describe a clear action to be performed
           - If the action involves file system, user interaction, or command execution, it should map to a tool call
           - Example: Instead of "Determine the contents of config.json", use "Use the `read_file` tool to get the content of 'config.json'"

        2. Tool Implication:
           - Phrase sub-tasks to clearly imply which tool the ReAct agent should use
           - Example: Instead of "Go to the src/utils directory and find all Python files", use:
             "Use the `list_files` tool to find all Python files in the 'src/utils' directory"
             OR
             "Use `search_files` with path 'src/utils' and file_pattern '*.py' to get Python files"

        3. Parameter Inclusion:
           - Include necessary parameters directly in the sub-task description
           - Example: Instead of "Create a new directory", use:
             "Create a placeholder file named '.gitkeep' inside a new directory 'my_project_folder' using `write_to_file`"

        4. User Interaction:
           - If information is needed from the user, MUST use the `request_user_input` tool
           - Example: "Use the `request_user_input` tool to ask the user for the desired project name, suggesting 'new_project'"

        5. Single, Concrete Step:
           - Each sub-task should represent a single, manageable step
           - Break complex operations into multiple sub-tasks
           - Example: Instead of "Set up the project structure and create initial files", split into:
             "Use `write_to_file` to create 'src/' directory with a '.gitkeep' file"
             "Use `write_to_file` to create 'tests/' directory with a '.gitkeep' file"
             "Use `write_to_file` to create 'docs/' directory with a '.gitkeep' file"

        6. Logical Order:
           - Sub-tasks must be in a sequence that makes sense
           - Consider dependencies between tasks
           - Example: Read files before modifying them, create directories before creating files in them

        7. Exhaustive Coverage:
           - The initial plan should attempt to cover all necessary steps
           - Include validation steps where appropriate
           - Example: After creating files, add "Use `read_file` to verify the content of 'config.json'"

        8. Avoid Abstract Actions:
           - Do not create subtasks like "Navigate to directory X" or "Understand the file structure"
           - Instead, create subtasks that use tools to achieve these goals
           - Example: "Use `list_files` on directory X to understand its structure"

        # HIGH-LEVEL USER GOAL
        {state.task}

        # OUTPUT FORMAT
        Based on the GOAL, the AVAILABLE TOOLS, and the SUBTASK GENERATION GUIDELINES, provide your response as a JSON object with a single key "subtasks". The value should be a list of strings, where each string is a sub-task description.

        Example JSON output:
        {{
            "subtasks": [
                "Use the `list_files` tool to list contents of the current directory.",
                "Use the `request_user_input` tool to ask the user which file they want to read from the list."
            ]
        }}
    """
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
