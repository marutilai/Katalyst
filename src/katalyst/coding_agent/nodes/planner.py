import os
from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.services.llms import (
    get_llm_client,
    get_llm_params,
)
from langchain_core.messages import AIMessage
from katalyst.katalyst_core.utils.models import SubtaskList, PlaybookEvaluation
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import extract_tool_descriptions
from katalyst.katalyst_core.utils.error_handling import (
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
    logger.debug("[PLANNER] Starting planner node...")
    logger.debug(f"[PLANNER][CONTENT_REF] Initial content_store state: {len(state.content_store)} references")

    # Use simplified API
    llm = get_llm_client("planner", async_mode=False, use_instructor=True)
    llm_params = get_llm_params("planner")
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
                **llm_params,
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
You are a planning assistant for an adaptive AI coding agent. Your job is to break down a high-level user GOAL into meaningful, goal-oriented tasks.

# AGENT CAPABILITIES
The agent is intelligent and can:
- Explore and understand project structures
- Make decisions based on discoveries
- Create additional subtasks if needed during execution
- Use various tools to accomplish goals

## Available Tool Categories:
- File operations (reading, writing, searching, renaming)
- Code analysis and manipulation  
- System operations and execution
- User interaction when needed
- Task decomposition for complex work

{playbook_section}

# PATH GUIDELINES
- Always use paths relative to project root (where 'katalyst' command was run)
- Include full paths from project root: 'folder/subfolder/file.py'

# PLANNING GUIDELINES

## 1. Recognize Simple vs Complex Tasks
For SIMPLE tasks (single file operation, one command, etc):
- Create just ONE task that captures the entire goal
- Don't break down into identify/execute/verify steps
- Examples: "Rename X to Y", "Delete file Z", "Run command ABC"

For COMPLEX tasks (building apps, multiple components, etc):
- Break down into logical, goal-oriented subtasks
- Group related work together

## 2. Focus on Outcomes, Not Tools
Create tasks that describe WHAT needs to be achieved, not HOW (specific tools).
- ❌ Avoid: "Use write_to_file to create app.py with imports..."
- ✅ Use: "Set up the main application entry point with basic configuration"
- ❌ Avoid: "Use list_files then read_file on each Python file"
- ✅ Use: "Analyze the existing codebase structure and patterns"

## 2. Logical Task Grouping
Group related work into cohesive tasks that make sense together.
- ❌ Avoid: "Create user.py", "Create auth.py", "Create middleware.py"
- ✅ Use: "Implement user authentication system with necessary models and middleware"
- ❌ Avoid: Multiple separate file creation tasks
- ✅ Use: "Set up project structure with core directories and configuration"

## 3. Appropriate Granularity
Tasks should be meaningful units of work - not too broad, not too specific.
- ❌ Too broad: "Build the entire application"
- ❌ Too specific: "Add import statement to main.py"
- ✅ Just right: "Implement the core Todo model with CRUD operations"

## 4. Allow for Discovery
Let the agent explore and make decisions based on what it finds.
- ❌ Avoid: "Create these exact 15 files: [long list]"
- ✅ Use: "Create project structure following Django best practices"
- ❌ Avoid: Prescribing exact implementation details
- ✅ Use: "Implement data validation based on model requirements"

## 5. Progressive Complexity
Order tasks from foundational to complex, allowing each to build on previous work.
- Start with setup/structure tasks
- Move to core functionality
- End with testing/documentation/polish

## 6. Consider Agent Autonomy
Remember the agent can create its own subtasks if it discovers complexity.
- Don't try to anticipate every micro-step
- Focus on logical, complete units of work
- Trust the agent to handle details

# HIGH-LEVEL USER GOAL
{state.task}

# OUTPUT FORMAT
Based on the GOAL and GUIDELINES{', and PLAYBOOK GUIDELINES' if playbook_guidelines else ''}, provide a JSON object with key "subtasks" containing a list of goal-oriented task descriptions.

Example for "Build a web application with user management":
{{
    "subtasks": [
        "Set up project structure and initial configuration",
        "Design and implement the data models",
        "Create the business logic layer",
        "Build the API or view layer",
        "Implement authentication and authorization",
        "Write comprehensive test coverage",
        "Add error handling and validation",
        "Create documentation"
    ]
}}

Note: This is a template showing the pattern - adapt the number and nature of tasks based on the actual goal complexity.

Remember: Focus on WHAT to achieve, not HOW to achieve it. The agent will figure out the specific tools and steps."""
    logger.debug(f"[PLANNER] Prompt to LLM:\n{prompt}")

    try:
        # Call the LLM with Instructor and Pydantic response model
        response = llm.chat.completions.create(
            messages=[{"role": "system", "content": prompt}],
            response_model=SubtaskList,
            temperature=0.3,
            model=llm_params["model"],
            timeout=llm_params["timeout"],
        )
        logger.debug(f"[PLANNER] Raw LLM response: {response}")
        subtasks = response.subtasks
        logger.debug(f"[PLANNER] Parsed subtasks: {subtasks}")

        # Update state
        state.task_queue = subtasks
        state.original_plan = subtasks  # Save the original plan
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

    logger.debug("[PLANNER] End of planner node.")
    return state
