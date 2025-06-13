import os
from src.katalyst_core.state import KatalystState
from src.katalyst_core.services.llms import get_llm_instructor
from langchain_core.messages import AIMessage
from src.katalyst_core.utils.models import SubtaskList, PlaybookEvaluation
from src.katalyst_core.utils.logger import get_logger
from src.katalyst_core.utils.tools import extract_tool_descriptions
from src.katalyst_core.utils.error_handling import (
    ErrorType,
    create_error_message,
    classify_error,
    format_error_for_llm,
)


def planner(state: KatalystState) -> KatalystState:
    """
    Generate initial subtask list in state.task_queue, set state.task_idx = 0, etc.
    Uses Instructor to get a structured list of subtasks from the LLM.
    If state.playbook_guidelines is provided, evaluate its relevance and use it appropriately.

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

    playbook_guidelines = getattr(state, "playbook_guidelines", None)

    # First, evaluate playbook relevance if guidelines exist
    if playbook_guidelines:
        evaluation_prompt = f"""
        # TASK
        Evaluate the relevance and applicability of the provided playbook guidelines to the current task.
        Think step by step about how well the guidelines match the task requirements.

        # CURRENT TASK
        {state.task}

        # PLAYBOOK GUIDELINES
        {playbook_guidelines}

        # EVALUATION CRITERIA
        1. Direct Relevance: How directly do the guidelines address the specific task?
        2. Completeness: Do the guidelines cover all necessary aspects of the task?
        3. Specificity: Are the guidelines specific enough to be actionable?
        4. Flexibility: Do the guidelines allow for necessary adaptations?

        # OUTPUT FORMAT
        Provide your evaluation as a JSON object with the following structure:
        {{
            "relevance_score": float,  # 0.0 to 1.0, where 1.0 means perfect relevance
            "is_directly_applicable": boolean,  # Whether guidelines can be used as strict requirements
            "key_guidelines": [string],  # List of most relevant guideline points
            "reasoning": string,  # Step-by-step explanation of your evaluation
            "usage_recommendation": string  # How to best use these guidelines (e.g., "strict", "reference", "ignore")
        }}
        """

        try:
            evaluation = llm.chat.completions.create(
                messages=[{"role": "system", "content": evaluation_prompt}],
                response_model=PlaybookEvaluation,
                temperature=0.1,
                model=os.getenv("KATALYST_LITELLM_MODEL", "gpt-4.1"),
            )
            logger.debug(f"[PLANNER] Playbook evaluation: {evaluation}")

            # Log the evaluation reasoning
            state.chat_history.append(
                AIMessage(content=f"Playbook evaluation:\n{evaluation.reasoning}")
            )

            # Adjust playbook section based on evaluation
            if evaluation.is_directly_applicable and evaluation.relevance_score > 0.8:
                playbook_section = f"""
                # PLAYBOOK GUIDELINES (STRICT REQUIREMENTS)
                These guidelines are highly relevant and must be followed strictly:
                {playbook_guidelines}
                """
            elif evaluation.relevance_score > 0.5:
                playbook_section = f"""
                # PLAYBOOK GUIDELINES (REFERENCE)
                These guidelines may be helpful but should be adapted as needed:
                {playbook_guidelines}
                """
            else:
                playbook_section = f"""
                # PLAYBOOK GUIDELINES (INFORMATIONAL)
                These guidelines are provided for reference but may not be directly applicable:
                {playbook_guidelines}
                """
        except Exception as e:
            logger.warning(f"[PLANNER] Failed to evaluate playbook: {str(e)}")
            playbook_section = f"""
            # PLAYBOOK GUIDELINES
            {playbook_guidelines}
            """
    else:
        playbook_section = ""

    prompt = f"""
        # ROLE
        You are a planning assistant for a ReAct-style AI agent. Your job is to break down a high-level user GOAL into a logically ordered list of atomic, executable sub-tasks. Each sub-task will be performed by an agent that can call tools, but cannot perform abstract reasoning or inference beyond what the tools enable.

        # AGENT CAPABILITIES
        The agent's primary capability is to use the tools provided below. Your plan should be entirely based on using these tools to achieve the goal.
        The agent has access to the following tools:
        {tool_list_str}

        # SUBTASK GUIDELINES
        {playbook_section}

        1. Actionable and Specific
        - Every sub-task must describe a clear, concrete action.
        - Avoid abstract goals like "analyze", "determine", "navigate".
        - Instead of: "Understand config file"
            Use: "Use 'read_file' to read 'config/settings.json' and summarize its key configuration parameters"

        2. Guiding Principles for Tool Selection
        - For high-level understanding of an entire codebase or directory, prefer 'generate_directory_overview' to get an efficient overview.
        - Only call 'generate_directory_overview' once per top-level directory (e.g., 'src/', 'app/'). It will recursively include all nested subdirectories and files, so there is no need to call it again for subdirectories within the same parent directory.
        - For focused work on a single, known file (reading to debug, edit, or get specific details), prefer the more direct 'read_file' tool.
        - Use 'list_code_definition_names' to get a quick map of functions/classes before diving deep with 'read_file'.
        - For getting a list of files, use the `list_files` tool.

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

        6. Logical Ordering
        - Ensure dependencies are respected.
        - Create directories or files before trying to read or write into them.
        - Read files before asking for analysis or summarization.

        7. Complete but Minimal
        - Cover all necessary steps implied by the goal.
        - Do not include extra steps unless explicitly required or implied.

        8. Avoid Abstract or Narrative Tasks
        - Avoid subtasks like "navigate to", "explore", or "think about".
        - Use tools like 'list_files' to perform directory inspection.

        # HIGH-LEVEL USER GOAL
        {state.task}

        # OUTPUT FORMAT
        Based on the GOAL, the AVAILABLE TOOLS, the AGENT CAPABILITIES, and the SUBTASK GUIDELINES{', and the PLAYBOOK GUIDELINES' if playbook_guidelines else ''}, provide your response as a JSON object with a single key "subtasks". The value should be a list of strings, where each string is a sub-task description.

        Example JSON output:
        {{
            "subtasks": [
                "Use the `list_files` tool to list contents of the current directory.",
                "Use the `read_file` tool to read 'README.md' and summarize its key features and requirements.",
                "Use the `request_user_input` tool to ask the user which file they want to analyze next."
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
