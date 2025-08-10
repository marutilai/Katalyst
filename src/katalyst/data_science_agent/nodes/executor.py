"""
Data Science Executor Node - Uses create_react_agent for data science task execution.

This node:
1. Creates an executor agent with tools for all data science workflows
2. Gets the current task from state (analysis, modeling, evaluation, etc.)
3. Executes only what was specifically requested
4. Sets AgentFinish when complete with suggested next steps
"""

from langchain_core.agents import AgentFinish
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.checkpointer_manager import checkpointer_manager
from katalyst.katalyst_core.config import get_llm_config
from katalyst.katalyst_core.utils.langchain_models import get_litellm_client
from katalyst.katalyst_core.utils.tools import (
    get_tool_functions_map,
    create_tools_with_context,
)
from katalyst.katalyst_core.utils.task_type_utils import parse_task_type, get_task_type_guidance
from katalyst.katalyst_core.utils.models import TaskType
from katalyst.app.execution_controller import check_execution_cancelled
from katalyst.app.config import USE_PLAYBOOKS
from katalyst.coding_agent.nodes.summarizer import get_summarization_node


# Data science execution prompt
executor_prompt = """You are a senior data scientist executing specific data science tasks.

Your role is to: 
- Understand the task assigned (analysis, modeling, evaluation, etc.)
- Save key results that would be useful for future analysis (e.g., feature rankings, important findings)

Use your tools to:
- Read data files (use execute_data_code with pd.read_csv(), pd.read_excel(), etc.)
- Execute code (execute_data_code for pandas, sklearn, visualization, etc. - maintains state)
- Save results (use execute_data_code with df.to_csv() for DataFrames, plt.savefig() for plots)
- Write metadata (save important findings as CSV, text, or images when they'd be useful for future analysis)
- Save trained models when appropriate (use joblib.dump() or pickle for model persistence)
- Search for additional data if needed (glob, grep)
- Run system commands if needed (bash)

FILE ORGANIZATION:
- Create organized output directories:
  - data/: Processed datasets, feature files, intermediate results
  - models/: Trained models, model artifacts, performance metrics
  - visualizations/: Charts, plots, graphs, visual analysis outputs
  - docs/: Reports, summaries, methodology documentation
- Use descriptive filenames that indicate the content

AVAILABLE LIBRARIES:
- pandas: Data manipulation, analysis, and file I/O (CSV, Excel, JSON, etc.)
- numpy: Numerical computing and array operations
- matplotlib: Basic plotting and visualization
- seaborn: Statistical data visualization
- scikit-learn (sklearn): Machine learning algorithms and utilities
- optuna: Hyperparameter optimization framework
"""


def executor(state: KatalystState) -> KatalystState:
    """
    Execute the current data science task using an executor agent with specialized tools.

    The agent will:
    - Take the current task (analysis, modeling, evaluation, etc.)
    - Execute only what was specifically requested
    - Provide results and suggest logical next steps
    - Mark task as complete with summary
    """
    logger = get_logger("data_science_agent")
    logger.debug("[DS_EXECUTOR] Starting data science executor node...")

    # Get checkpointer from manager
    checkpointer = checkpointer_manager.get_checkpointer()
    
    # Check if we have a checkpointer
    if not checkpointer:
        logger.error("[DS_EXECUTOR] No checkpointer available from manager")
        state.error_message = "No checkpointer available for conversation"
        return state

    # Get current task
    if state.task_idx >= len(state.task_queue):
        logger.warning("[DS_EXECUTOR] No more tasks in queue")
        return state

    current_task = state.task_queue[state.task_idx]
    logger.info(f"[DS_EXECUTOR] Working on task: {current_task}")

    # Get configured model
    llm_config = get_llm_config()
    model_name = llm_config.get_model_for_component("executor")
    provider = llm_config.get_provider()
    timeout = llm_config.get_timeout()
    api_base = llm_config.get_api_base()

    logger.debug(f"[DS_EXECUTOR] Using model: {model_name} (provider: {provider})")

    # Get executor model
    executor_model = get_litellm_client(
        model_name=model_name,
        provider=provider,
        temperature=0,
        timeout=timeout,
        api_base=api_base,
    )

    # Get executor tools with logging context
    tool_functions = get_tool_functions_map(category="executor")
    tools = create_tools_with_context(tool_functions, "DS_EXECUTOR", state)

    # Get summarization node for conversation compression
    summarization_node = get_summarization_node()

    # Create executor agent with summarization
    executor_agent = create_react_agent(
        model=executor_model,
        tools=tools,
        checkpointer=checkpointer,
        prompt=executor_prompt,  # Set as system prompt
        pre_model_hook=summarization_node,  # Enable conversation summarization
    )

    # Parse task type and get specialized guidance if USE_PLAYBOOKS is enabled
    specialized_guidance = ""
    if USE_PLAYBOOKS:
        task_type, clean_task = parse_task_type(current_task)
        if task_type and task_type != TaskType.OTHER:
            specialized_guidance = get_task_type_guidance(task_type)
            logger.debug(f"[DS_EXECUTOR] Detected task type: {task_type.value}")
            # Log the clean task description
            logger.debug(f"[DS_EXECUTOR] Task description: {clean_task}")
    
    # Create task message with optional specialized guidance
    task_content = f"""Now, please complete this task:

Task: {current_task}

IMPORTANT: Use auto_approve={state.auto_approve} when calling file modification tools (write, edit, multiedit).
"""
    
    # Add specialized guidance section if available
    if specialized_guidance:
        task_content += f"""
## Best Practices and Guidelines

The following guidelines are recommended best practices for this type of task:

{specialized_guidance}
"""
    
    task_content += """
Remember: Do ONLY what this specific task asks for. Don't go beyond the request.

When you have completed the task, respond with:

TASK COMPLETED:
[Brief summary of what you did]

SUGGESTED NEXT STEPS:
1. [Natural follow-up task based on what you found]
2. [Another logical next step]
3. [A third option for further exploration]"""
    
    # Add task message to conversation
    task_message = HumanMessage(content=task_content)

    # Add to messages
    state.messages.append(task_message)

    try:
        # Check if execution was cancelled
        check_execution_cancelled("ds_executor")

        # Execute with the agent
        logger.info("[DS_EXECUTOR] Invoking executor agent")
        logger.debug(f"[DS_EXECUTOR] Message count before: {len(state.messages)}")

        result = executor_agent.invoke({"messages": state.messages})

        # Update messages with the full conversation
        state.messages = result.get("messages", state.messages)
        logger.debug(f"[DS_EXECUTOR] Message count after: {len(state.messages)}")

        # Look for the last AI message to check if task is complete
        ai_messages = [msg for msg in state.messages if isinstance(msg, AIMessage)]

        if ai_messages:
            last_message = ai_messages[-1]

            # Check if task is marked as complete
            if "TASK COMPLETED:" in last_message.content:
                # Extract summary after "TASK COMPLETED:"
                summary_parts = last_message.content.split("TASK COMPLETED:", 1)
                summary = summary_parts[1].strip()

                # Task is complete
                state.agent_outcome = AgentFinish(
                    return_values={"output": summary}, log=""
                )
                logger.info(f"[DS_EXECUTOR] Task completed: {summary[:100]}...")
            else:
                # Task not complete yet - this shouldn't happen with create_react_agent
                # as it runs until completion, but handle it just in case
                logger.warning("[DS_EXECUTOR] Agent returned without completing task")
                state.error_message = "Agent did not complete the task"

            # Update tool execution history from the conversation
            for msg in state.messages:
                if isinstance(msg, ToolMessage):
                    execution_record = {
                        "task": current_task,
                        "tool_name": msg.name,
                        "status": "success" if "Error" not in msg.content else "error",
                        "summary": msg.content[:100] + "..."
                        if len(msg.content) > 100
                        else msg.content,
                    }
                    # Check if this record already exists to avoid duplicates
                    if execution_record not in state.tool_execution_history:
                        state.tool_execution_history.append(execution_record)
        else:
            # No AI response
            state.error_message = "Agent did not provide a response"
            logger.error("[DS_EXECUTOR] No AI response from agent")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[DS_EXECUTOR] Error during execution: {error_msg}")
        state.error_message = f"Task execution error: {error_msg}"

    # Clear error message if successful
    if state.agent_outcome and isinstance(state.agent_outcome, AgentFinish):
        state.error_message = None

    logger.debug("[DS_EXECUTOR] End of data science executor node.")
    return state
