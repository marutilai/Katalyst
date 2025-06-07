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
        # ROLE
        You are a planning assistant for a ReAct-style AI agent. Your job is to break down a high-level user GOAL into a logically ordered list of atomic, executable sub-tasks. Each sub-task will be performed by an agent that can call tools, but cannot perform abstract reasoning or inference beyond what the tools enable.

        # TOOL AWARENESS
        The agent executing your sub-tasks has access to the following tools:
        {tool_list_str}

        Constraints:
        - The agent cannot navigate directories or inspect file systems directly.
        - All file operations must use tools that accept explicit paths (e.g., 'list_files', 'read_file', 'write_to_file').

        # SUBTASK GUIDELINES

        1. Actionable and Specific
        - Every sub-task must describe a clear, concrete action.
        - Avoid abstract goals like "analyze", "determine", "navigate".
        - Instead of: "Understand config file"
            Use: "Use 'read_file' to read 'config/settings.json'"

        2. Tool-Oriented
        - Phrase each sub-task so that it clearly maps to a known tool.
        - Prefer clarity and determinism over brevity.

        3. Parameter-Specific
        - Include all required parameters inline (e.g., filenames, paths, content).
        - Instead of: "Create a file"
            Use: "Use 'write_to_file' to create 'README.md' with the content 'Initial setup'"

        4. Explicit User Interaction
        - If input is needed from the user, use 'request_user_input' and specify the prompt.
        - Example: "Use 'request_user_input' to ask the user for the desired output folder, defaulting to 'output/'"

        5. Single-Step Granularity
        - Sub-tasks should be atomic and non-composite.
        - Avoid bundling multiple steps into one.
        - Instead of: "Set up project structure"
            Use:
            - "Use 'write_to_file' to create empty file 'src/main.py'"
            - "Use 'write_to_file' to create empty file 'tests/test_main.py'"

        6. Logical Ordering
        - Ensure dependencies are respected.
        - Create directories or files before trying to read or write into them.

        7. Complete but Minimal
        - Cover all necessary steps implied by the goal.
        - Do not include extra steps unless explicitly required or implied.

        8. Avoid Abstract or Narrative Tasks
        - Avoid subtasks like "navigate to", "explore", or "think about".
        - Use tools like 'list_files' to perform directory inspection.

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
            model=os.getenv("KATALYST_LITELLM_MODEL", "gpt-4.1"),
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
