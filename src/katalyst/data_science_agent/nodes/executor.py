"""
Data Science Executor Node - Uses create_react_agent for analysis task execution.

This node:
1. Creates an executor agent with all tools including data analysis capabilities
2. Gets the current investigation task from state
3. Uses the agent to explore data and generate insights
4. Sets AgentFinish when the investigation is complete
"""

from langchain_core.agents import AgentFinish
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.config import get_llm_config
from katalyst.katalyst_core.utils.langchain_models import get_langchain_chat_model
from katalyst.katalyst_core.utils.tools import get_tool_functions_map, create_tools_with_context
from katalyst.app.execution_controller import check_execution_cancelled
from katalyst.coding_agent.nodes.summarizer import get_summarization_node


# Data science execution prompt
executor_prompt = """You are a senior data scientist executing analysis tasks.

Your role is to:
1. Understand the specific investigation task assigned
2. Load and explore data to answer the question at hand
3. Generate insights through analysis and visualization
4. Document findings clearly with evidence

Use your tools to:
- Read data files (read_file for CSVs, JSONs, etc.)
- Execute analysis code (execute_data_code for pandas, visualization, etc.)
- Run system commands for data processing (bash)
- Save results and visualizations (write_file)
- Search for additional data if needed (search_files, grep)

ANALYSIS GUIDELINES:
- Let data guide your investigation, don't force preconceptions
- Start simple, build complexity as understanding grows
- Validate assumptions before proceeding
- Create visualizations to communicate findings
- Document data quality issues encountered
- Provide statistical evidence for claims

IMPORTANT: Focus on discovering insights, not just running code.
Each task should produce findings that inform the overall analysis.

When loading data, handle common issues gracefully:
- Check encoding if files fail to load
- Handle missing values appropriately
- Validate data types match expectations
- Document any data quality issues found
"""


def executor(state: KatalystState) -> KatalystState:
    """
    Execute the current analysis task using an executor agent with data science tools.
    
    The agent will:
    - Take the current investigation task
    - Load and analyze data as needed
    - Generate insights and visualizations
    - Return findings when complete
    """
    logger = get_logger()
    logger.debug("[DS_EXECUTOR] Starting data science executor node...")
    
    # Check if we have a checkpointer
    if not state.checkpointer:
        logger.error("[DS_EXECUTOR] No checkpointer found in state")
        state.error_message = "No checkpointer available for conversation"
        return state
    
    # Get current task
    if state.task_idx >= len(state.task_queue):
        logger.warning("[DS_EXECUTOR] No more tasks in queue")
        return state
        
    current_task = state.task_queue[state.task_idx]
    logger.info(f"[DS_EXECUTOR] Working on analysis task: {current_task}")
    
    # Get configured model
    llm_config = get_llm_config()
    model_name = llm_config.get_model_for_component("executor")
    provider = llm_config.get_provider()
    timeout = llm_config.get_timeout()
    api_base = llm_config.get_api_base()
    
    logger.debug(f"[DS_EXECUTOR] Using model: {model_name} (provider: {provider})")
    
    # Get executor model
    executor_model = get_langchain_chat_model(
        model_name=model_name,
        provider=provider,
        temperature=0,
        timeout=timeout,
        api_base=api_base
    )
    
    # Get executor tools with logging context
    tool_functions = get_tool_functions_map(category="executor")
    tools = create_tools_with_context(tool_functions, "DS_EXECUTOR")
    
    # Get summarization node for conversation compression
    summarization_node = get_summarization_node()
    
    # Create executor agent with summarization
    executor_agent = create_react_agent(
        model=executor_model,
        tools=tools,
        checkpointer=state.checkpointer,
        prompt=executor_prompt,  # Set as system prompt
        pre_model_hook=summarization_node  # Enable conversation summarization
    )
    
    # Add task message to conversation
    task_message = HumanMessage(content=f"""Now, please complete this analysis task:

Task: {current_task}

Focus on generating insights and findings. Use data to support your conclusions.
Create visualizations where helpful. Document any data quality issues.

When you have completed the investigation, respond with "TASK COMPLETED:" followed by a summary of your findings.""")
    
    # Add to messages
    state.messages.append(task_message)
    
    try:
        # Check if execution was cancelled
        check_execution_cancelled("ds_executor")
        
        # Execute with the agent
        logger.info(f"[DS_EXECUTOR] Invoking executor agent for analysis")
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
                summary = summary_parts[1].strip() if len(summary_parts) > 1 else last_message.content
                
                # Task is complete
                state.agent_outcome = AgentFinish(
                    return_values={"output": summary},
                    log=""
                )
                logger.info(f"[DS_EXECUTOR] Analysis task completed: {summary[:100]}...")
            else:
                # Task not complete yet - this shouldn't happen with create_react_agent
                # as it runs until completion, but handle it just in case
                logger.warning("[DS_EXECUTOR] Agent returned without completing task")
                state.error_message = "Agent did not complete the analysis task"
            
            # Update tool execution history from the conversation
            for msg in state.messages:
                if isinstance(msg, ToolMessage):
                    execution_record = {
                        "task": current_task,
                        "tool_name": msg.name,
                        "status": "success" if "Error" not in msg.content else "error", 
                        "summary": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
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
        state.error_message = f"Analysis execution error: {error_msg}"
    
    # Clear error message if successful
    if state.agent_outcome and isinstance(state.agent_outcome, AgentFinish):
        state.error_message = None
    
    logger.debug("[DS_EXECUTOR] End of data science executor node.")
    return state