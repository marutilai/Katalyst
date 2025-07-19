"""
Executor Node - Uses create_react_agent for task execution.

This node:
1. Creates an executor agent with all tools
2. Gets the current task from state
3. Uses the agent to implement the task
4. Sets AgentFinish when the task is complete
"""

from typing import Dict, Any
from langchain_core.agents import AgentFinish
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.config import get_llm_config
from katalyst.katalyst_core.utils.langchain_models import get_langchain_chat_model
from katalyst.katalyst_core.utils.tools import get_tool_functions_map, create_tools_with_context
from katalyst.app.execution_controller import check_execution_cancelled


def executor(state: KatalystState) -> KatalystState:
    """
    Execute the current task using an executor agent with all tools.
    
    The agent will:
    - Take the current task
    - Use tools as needed
    - Return when the task is complete
    """
    logger = get_logger()
    logger.debug("[EXECUTOR] Starting executor node...")
    
    # Check if we have a checkpointer
    if not state.checkpointer:
        logger.error("[EXECUTOR] No checkpointer found in state")
        state.error_message = "No checkpointer available for conversation"
        return state
    
    # Get current task
    if state.task_idx >= len(state.task_queue):
        logger.warning("[EXECUTOR] No more tasks in queue")
        return state
        
    current_task = state.task_queue[state.task_idx]
    logger.info(f"[EXECUTOR] Working on task: {current_task}")
    
    # Get configured model
    llm_config = get_llm_config()
    model_name = llm_config.get_model_for_component("executor")
    provider = llm_config.get_provider()
    timeout = llm_config.get_timeout()
    api_base = llm_config.get_api_base()
    
    logger.debug(f"[EXECUTOR] Using model: {model_name} (provider: {provider})")
    
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
    tools = create_tools_with_context(tool_functions, "EXECUTOR")
    
    # Create executor agent
    executor_agent = create_react_agent(
        model=executor_model,
        tools=tools,
        checkpointer=state.checkpointer
    )
    
    # Add task message to conversation
    task_message = HumanMessage(content=f"""Now, please complete this task:

Task: {current_task}

IMPORTANT: To complete this task, you must actually implement it by creating/modifying files. 
A task is only complete when the code is written and functional, not when you've described what to do.
If you need to make assumptions, make reasonable ones and proceed with implementation.

When you have fully completed the implementation, respond with "TASK COMPLETED:" followed by a summary of what was done.""")
    
    # Add to messages
    state.messages.append(task_message)
    
    try:
        # Check if execution was cancelled
        check_execution_cancelled("executor")
        
        # Execute with the agent
        logger.info(f"[EXECUTOR] Invoking executor agent")
        logger.debug(f"[EXECUTOR] Message count before: {len(state.messages)}")
        
        result = executor_agent.invoke({"messages": state.messages})
        
        # Update messages with the full conversation
        state.messages = result.get("messages", state.messages)
        logger.debug(f"[EXECUTOR] Message count after: {len(state.messages)}")
        
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
                logger.info(f"[EXECUTOR] Task completed: {summary[:100]}...")
            else:
                # Task not complete yet - this shouldn't happen with create_react_agent
                # as it runs until completion, but handle it just in case
                logger.warning("[EXECUTOR] Agent returned without completing task")
                state.error_message = "Agent did not complete the task"
            
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
            logger.error("[EXECUTOR] No AI response from agent")
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[EXECUTOR] Error during execution: {error_msg}")
        state.error_message = f"Agent execution error: {error_msg}"
    
    # Clear error message if successful
    if state.agent_outcome and isinstance(state.agent_outcome, AgentFinish):
        state.error_message = None
    
    logger.debug("[EXECUTOR] End of executor node.")
    return state