"""
React Agent Node - Uses persistent create_react_agent for task execution.

This node:
1. Gets the current task from state
2. Continues the conversation with the persistent agent
3. Sets AgentFinish when the task is complete
"""

from typing import Dict, Any
from langchain_core.agents import AgentFinish
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.logger import get_logger


def agent_react(state: KatalystState) -> KatalystState:
    """
    Continue the conversation with the persistent agent for the current task.
    
    The agent will:
    - Take the current task
    - Use tools as needed
    - Return when the task is complete
    """
    logger = get_logger()
    
    # Check if we have an agent
    if not state.agent_executor:
        logger.error("[AGENT_REACT] No agent executor found in state")
        state.error_message = "No agent executor available"
        return state
    
    # Get current task
    if state.task_idx >= len(state.task_queue):
        logger.warning("[AGENT_REACT] No more tasks in queue")
        return state
        
    current_task = state.task_queue[state.task_idx]
    logger.info(f"[AGENT_REACT] Working on task: {current_task}")
    
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
        # Continue the conversation with the persistent agent
        logger.info(f"[AGENT_REACT] Continuing conversation with persistent agent")
        logger.debug(f"[AGENT_REACT] Message count before: {len(state.messages)}")
        
        result = state.agent_executor.invoke({"messages": state.messages})
        
        # Update messages with the full conversation
        state.messages = result.get("messages", state.messages)
        logger.debug(f"[AGENT_REACT] Message count after: {len(state.messages)}")
        
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
                logger.info(f"[AGENT_REACT] Task completed: {summary[:100]}...")
            else:
                # Task not complete yet - this shouldn't happen with create_react_agent
                # as it runs until completion, but handle it just in case
                logger.warning("[AGENT_REACT] Agent returned without completing task")
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
            logger.error("[AGENT_REACT] No AI response from agent")
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[AGENT_REACT] Error during execution: {error_msg}")
        state.error_message = f"Agent execution error: {error_msg}"
    
    # Clear error message if successful
    if state.agent_outcome and isinstance(state.agent_outcome, AgentFinish):
        state.error_message = None
    
    return state