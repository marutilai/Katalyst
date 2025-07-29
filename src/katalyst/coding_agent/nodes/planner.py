"""
Planner Node - Uses create_react_agent for intelligent planning.

This node:
1. Creates a planner agent with exploration tools
2. Uses the agent to explore the codebase and create a plan
3. Extracts subtasks from the agent's response
4. Updates state with the plan
"""

from typing import List
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent

from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.models import PlannerOutput, EnhancedPlannerOutput
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.checkpointer_manager import checkpointer_manager
from katalyst.katalyst_core.config import get_llm_config
from katalyst.app.config import USE_PLAYBOOKS
from katalyst.katalyst_core.utils.langchain_models import get_langchain_chat_model
from katalyst.katalyst_core.utils.tools import (
    get_tool_functions_map,
    create_tools_with_context,
)
from katalyst.coding_agent.nodes.summarizer import get_summarization_node


# Planning-focused prompt
planner_prompt = """You are a senior software architect creating implementation plans.

CRITICAL: You are in the PLANNING phase. DO NOT execute any actions or make any changes!

Your role is to:
1. ANALYZE the current state of the codebase/filesystem
2. UNDERSTAND what needs to be built
3. CREATE a detailed plan for implementation

You are ONLY allowed to:
- Explore directory structure (ls) - to understand what exists
- Search for patterns (grep, glob) - to find relevant code
- Read files (read) - to understand existing architecture
- Find code definitions (list_code_definitions) - to understand code structure
- Ask questions (request_user_input) - when you need clarification

You MUST NOT:
- Create any files or directories
- Execute any commands
- Make any modifications
- Install any packages
- Run any builds or tests

PLANNING GUIDELINES:
- Each task should be a complete, actionable instruction
- Tasks should be roughly equal in scope
- Tasks should build on each other logically
- Include all setup, implementation, and testing tasks
- Be specific about file paths and component names

After exploring and understanding the requirements, provide your plan as a list of subtasks.

Example subtask format:
- Set up project directory structure with appropriate subdirectories
- Initialize development environment and install required dependencies
- Create core application architecture and entry points
- Implement data models and database schema
- Build API endpoints with proper routing and validation
- Develop frontend components and user interface
- Integrate frontend with backend services
- Write unit tests for critical functionality
- Add integration tests for API endpoints
- Configure deployment and build processes
"""

# Enhanced prompt with task classification
enhanced_planner_prompt = """You are a senior software architect creating implementation plans.

CRITICAL: You are in the PLANNING phase. DO NOT execute any actions or make any changes!

Your role is to:
1. ANALYZE the current state of the codebase/filesystem
2. UNDERSTAND what needs to be built
3. CREATE a detailed plan for implementation
4. CLASSIFY each task by type

You are ONLY allowed to:
- Explore directory structure (ls) - to understand what exists
- Search for patterns (grep, glob) - to find relevant code
- Read files (read) - to understand existing architecture
- Find code definitions (list_code_definitions) - to understand code structure
- Ask questions (request_user_input) - when you need clarification

You MUST NOT:
- Create any files or directories
- Execute any commands
- Make any modifications
- Install any packages
- Run any builds or tests

PLANNING GUIDELINES:
- Each task should be a complete, actionable instruction
- Tasks should be roughly equal in scope
- Tasks should build on each other logically
- Include all setup, implementation, and testing tasks
- Be specific about file paths and component names

TASK CLASSIFICATION:
For each task, assign one of these types:
- test_creation: Writing new tests (unit, integration, e2e)
- refactor: Improving code structure without changing functionality
- documentation: Writing docs, comments, READMEs
- data_exploration: Analyzing tabular datasets, EDA
- feature_engineering: Creating features for ML/AI models
- model_training: Training ML/AI models
- model_evaluation: Testing ML/AI model performance
- model_deployment: Deploying ML/AI models
- other: Anything else

After exploring and understanding the requirements, provide your plan as a list of classified subtasks."""


def planner(state: KatalystState) -> KatalystState:
    """
    Use a planning agent to explore the codebase and create an implementation plan.
    """
    logger = get_logger("coding_agent")
    logger.debug("[PLANNER] Starting planner node...")

    # Get checkpointer from manager
    checkpointer = checkpointer_manager.get_checkpointer()

    # Check if we have a checkpointer
    if not checkpointer:
        logger.error("[PLANNER] No checkpointer available from manager")
        state.error_message = "No checkpointer available for conversation"
        return state

    # Get configured model
    llm_config = get_llm_config()
    model_name = llm_config.get_model_for_component("planner")
    provider = llm_config.get_provider()
    timeout = llm_config.get_timeout()
    api_base = llm_config.get_api_base()

    logger.debug(f"[PLANNER] Using model: {model_name} (provider: {provider})")

    # Get planner model
    planner_model = get_langchain_chat_model(
        model_name=model_name,
        provider=provider,
        temperature=0,
        timeout=timeout,
        api_base=api_base,
    )

    # Get planner tools with logging context
    tool_functions = get_tool_functions_map(category="planner")
    tools = create_tools_with_context(tool_functions, "PLANNER")

    # Get summarization node for conversation compression
    summarization_node = get_summarization_node()

    # Select appropriate prompt and output format based on USE_PLAYBOOKS
    if USE_PLAYBOOKS:
        selected_prompt = enhanced_planner_prompt
        output_format = EnhancedPlannerOutput
        logger.debug("[PLANNER] Using enhanced planner with task classification")
    else:
        selected_prompt = planner_prompt
        output_format = PlannerOutput
        logger.debug("[PLANNER] Using standard planner")

    # Create planner agent with structured output and summarization
    planner_agent = create_react_agent(
        model=planner_model,
        tools=tools,
        checkpointer=checkpointer,
        prompt=selected_prompt,  # Set as system prompt
        response_format=output_format,  # Use structured output
        pre_model_hook=summarization_node,  # Enable conversation summarization
    )

    # Create user request message
    user_request_message = HumanMessage(
        content=f"""User Request: {state.task}

Please explore the codebase as needed and create a detailed implementation plan.
Provide your final plan as a list of subtasks that can be executed to complete the request."""
    )

    # Initialize messages if needed
    if not state.messages:
        state.messages = []

    # Add user request message
    state.messages.append(user_request_message)

    try:
        # Use the planner agent to create a plan
        logger.info("[PLANNER] Invoking planner agent to create plan")
        result = planner_agent.invoke({"messages": state.messages})

        # Update messages
        state.messages = result.get("messages", state.messages)

        # Extract structured response
        structured_response = result.get("structured_response")

        if structured_response and (
            isinstance(structured_response, PlannerOutput)
            or isinstance(structured_response, EnhancedPlannerOutput)
        ):
            subtasks = structured_response.subtasks

            if subtasks:
                # Handle different output formats
                if isinstance(structured_response, EnhancedPlannerOutput):
                    # Enhanced output with TaskInfo objects
                    # Prefix each task with its type in brackets
                    task_strings = [
                        f"[{task.task_type.value.upper()}] {task.description}"
                        for task in subtasks
                    ]

                    # Log the plan with task types
                    plan_message = f"Generated plan with task types:\n" + "\n".join(
                        f"{i+1}. {task_str}"
                        for i, task_str in enumerate(task_strings)
                    )
                else:
                    # Standard output with strings
                    task_strings = subtasks

                    # Log the plan
                    plan_message = f"Generated plan:\n" + "\n".join(
                        f"{i+1}. {s}" for i, s in enumerate(subtasks)
                    )

                # Update state with the plan (as strings for now)
                state.task_queue = task_strings
                state.original_plan = task_strings
                state.task_idx = 0
                state.outer_cycles = 0
                state.completed_tasks = []
                state.error_message = None
                state.plan_feedback = None

                logger.info(f"[PLANNER] {plan_message}")
            else:
                logger.error("[PLANNER] Structured response contained no subtasks")
                state.error_message = "Plan was empty"
        else:
            # Fallback: check if there's an error message in the result
            logger.error(
                f"[PLANNER] No structured response received. Result keys: {list(result.keys())}"
            )
            state.error_message = "Failed to get structured plan from agent"

            # Log any AI messages for debugging
            ai_messages = [msg for msg in state.messages if isinstance(msg, AIMessage)]
            if ai_messages:
                logger.debug(
                    f"[PLANNER] Last AI message: {ai_messages[-1].content[:200]}..."
                )

    except Exception as e:
        logger.error(f"[PLANNER] Failed to generate plan: {str(e)}")
        state.error_message = f"Failed to generate plan: {str(e)}"

    logger.debug("[PLANNER] End of planner node.")
    return state
