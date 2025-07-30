"""
Data Science Planner Node - Uses create_react_agent for intelligent analysis planning.

This node:
1. Creates a planner agent with exploration tools
2. Uses the agent to understand the data and create an analysis plan
3. Extracts investigation tasks from the agent's response
4. Updates state with the plan
"""

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


# Data science planning prompt
planner_prompt = """You are a senior data scientist creating data science workflows.

Your role is to:
1. Understand the data science request and objectives
2. Explore available data sources and their structure
3. Break down the work into logical, focused tasks
4. Create a plan appropriate for the specific type of work requested

Use your tools to:
- List data files and check their formats (ls)
- Search for relevant datasets (search_files, glob)
- For CSV/Excel files: Use execute_data_code with pd.read_csv() or pd.read_excel() to peek at structure
  Example: execute_data_code("df = pd.read_csv('data.csv'); print(df.shape); print(df.columns.tolist())")
- For text/JSON/other files: Use read tool
- Ask for clarification if the objectives are unclear (request_user_input)

PLANNING GUIDELINES BY TASK TYPE:

For Exploratory Analysis:
- Start with data profiling and quality assessment
- Identify patterns, anomalies, and relationships
- Create meaningful visualizations

For Predictive Modeling:
- Data preparation and feature engineering
- Model training with appropriate algorithms
- Evaluation using relevant metrics
- Model comparison and selection

For Statistical Analysis:
- Hypothesis formulation
- Statistical test selection
- Results interpretation and validation

For Model Evaluation:
- Performance metrics calculation
- Cross-validation or holdout testing
- Error analysis and diagnostics

For Deployment Preparation:
- Model serialization
- Input/output specifications
- Performance optimization

IMPORTANT: Create focused tasks that directly address what was requested.
Don't add extra exploration unless specifically asked for.

Example workflows:

Categorical Variable Analysis:
- Load data and identify all categorical variables
- Calculate frequency distributions for each categorical variable
- Visualize distributions with appropriate charts
- Analyze relationships between categorical variables

Predictive Model Development:
- Load and prepare training/test datasets
- Engineer relevant features for the prediction task
- Train multiple model types (e.g., logistic regression, random forest)
- Evaluate models using appropriate metrics
- Select best model based on performance

Time Series Forecasting:
- Load time series data and check temporal coverage
- Analyze trends, seasonality, and stationarity
- Apply appropriate forecasting methods
- Validate forecasts using holdout period
- Generate future predictions with confidence intervals

After exploring the available data and understanding the objectives, provide your plan as a list of focused tasks."""

# Enhanced prompt with task classification for data science
enhanced_planner_prompt = """You are a senior data scientist creating data science workflows.

Your role is to:
1. Understand the data science request and objectives
2. Explore available data sources and their structure
3. Break down the work into logical, focused tasks
4. Create a plan appropriate for the specific type of work requested
5. CLASSIFY each task by type

Use your tools to:
- List data files and check their formats (ls)
- Search for relevant datasets (search_files, glob)
- For CSV/Excel files: Use execute_data_code with pd.read_csv() or pd.read_excel() to peek at structure
  Example: execute_data_code("df = pd.read_csv('data.csv'); print(df.shape); print(df.columns.tolist())")
- For text/JSON/other files: Use read tool
- Ask for clarification if the objectives are unclear (request_user_input)

PLANNING GUIDELINES BY TASK TYPE:

For Exploratory Analysis:
- Start with data profiling and quality assessment
- Identify patterns, anomalies, and relationships
- Create meaningful visualizations

For Predictive Modeling:
- Data preparation and feature engineering
- Model training with appropriate algorithms
- Evaluation using relevant metrics
- Model comparison and selection

For Statistical Analysis:
- Hypothesis formulation
- Statistical test selection
- Results interpretation and validation

For Model Evaluation:
- Performance metrics calculation
- Cross-validation or holdout testing
- Error analysis and diagnostics

For Deployment Preparation:
- Model serialization
- Input/output specifications
- Performance optimization

TASK CLASSIFICATION:
For each task, assign one of these types:
- test_creation: Writing new tests (unit, integration, e2e)
- refactor: Improving code structure without changing functionality
- documentation: Creating reports, documenting findings, comments, READMEs
- data_exploration: Initial data analysis, EDA, understanding data
- feature_engineering: Data preprocessing, cleaning, missing values, encoding, scaling, creating new features, transformations
- model_training: Training ML/AI models
- model_evaluation: Testing and evaluating model performance
- other: Anything else other than the above

IMPORTANT: Create focused tasks that directly address what was requested. Don't add extra exploration unless specifically asked for.

After exploring the available data and understanding the objectives, provide your plan as a list of classified subtasks."""


def planner(state: KatalystState) -> KatalystState:
    """
    Use a planning agent to explore data sources and create an analysis plan.
    """
    logger = get_logger("data_science_agent")
    logger.debug("[DS_PLANNER] Starting data science planner node...")

    # Get checkpointer from manager
    checkpointer = checkpointer_manager.get_checkpointer()

    # Check if we have a checkpointer
    if not checkpointer:
        logger.error("[DS_PLANNER] No checkpointer available from manager")
        state.error_message = "No checkpointer available for conversation"
        return state

    logger.debug(f"[DS_PLANNER] Got checkpointer from manager: {type(checkpointer)}")

    # Get configured model
    llm_config = get_llm_config()
    model_name = llm_config.get_model_for_component("planner")
    provider = llm_config.get_provider()
    timeout = llm_config.get_timeout()
    api_base = llm_config.get_api_base()

    logger.debug(f"[DS_PLANNER] Using model: {model_name} (provider: {provider})")

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
    tools = create_tools_with_context(tool_functions, "DS_PLANNER")

    # Get summarization node for conversation compression
    summarization_node = get_summarization_node()

    # Select appropriate prompt and output format based on USE_PLAYBOOKS
    if USE_PLAYBOOKS:
        selected_prompt = enhanced_planner_prompt
        output_format = EnhancedPlannerOutput
        logger.debug("[DS_PLANNER] Using enhanced planner with task classification")
    else:
        selected_prompt = planner_prompt
        output_format = PlannerOutput
        logger.debug("[DS_PLANNER] Using standard planner")

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
        content=f"""Data Science Request: {state.task}

Please explore the available data and create a focused workflow.
Create only the tasks needed to complete what was specifically requested."""
    )

    # Initialize messages if needed
    if not state.messages:
        state.messages = []

    # Add user request message
    state.messages.append(user_request_message)

    try:
        # Use the planner agent to create a plan
        logger.info("[DS_PLANNER] Invoking planner agent to create analysis plan")
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
                    plan_message = (
                        f"Generated analysis plan with task types:\n"
                        + "\n".join(
                            f"{i+1}. {task_str}"
                            for i, task_str in enumerate(task_strings)
                        )
                    )
                else:
                    # Standard output with strings
                    task_strings = subtasks

                    # Log the plan
                    plan_message = f"Generated analysis plan:\n" + "\n".join(
                        f"{i+1}. {s}" for i, s in enumerate(subtasks)
                    )

                # Update state with the plan
                state.task_queue = task_strings
                state.original_plan = task_strings
                state.task_idx = 0
                state.outer_cycles = 0
                state.completed_tasks = []
                state.error_message = None
                state.plan_feedback = None

                logger.info(f"[DS_PLANNER] {plan_message}")
            else:
                logger.error("[DS_PLANNER] Structured response contained no subtasks")
                state.error_message = "Plan was empty"
        else:
            # Fallback: check if there's an error message in the result
            logger.error(
                f"[DS_PLANNER] No structured response received. Result keys: {list(result.keys())}"
            )
            state.error_message = "Failed to get structured plan from agent"

            # Log any AI messages for debugging
            ai_messages = [msg for msg in state.messages if isinstance(msg, AIMessage)]
            if ai_messages:
                logger.debug(
                    f"[DS_PLANNER] Last AI message: {ai_messages[-1].content[:200]}..."
                )

    except Exception as e:
        logger.error(f"[DS_PLANNER] Failed to generate plan: {str(e)}")
        state.error_message = f"Failed to generate plan: {str(e)}"

    logger.debug("[DS_PLANNER] End of data science planner node.")
    return state
