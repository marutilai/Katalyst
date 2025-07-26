"""
Executor Node - Uses create_react_agent for task execution.

This node:
1. Creates an executor agent with all tools
2. Gets the current task from state
3. Uses the agent to implement the task
4. Sets AgentFinish when the task is complete
"""

from langchain_core.agents import AgentFinish
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.checkpointer_manager import checkpointer_manager
from katalyst.katalyst_core.config import get_llm_config
from katalyst.katalyst_core.utils.langchain_models import get_langchain_chat_model
from katalyst.katalyst_core.utils.tools import get_tool_functions_map, create_tools_with_context
from katalyst.app.execution_controller import check_execution_cancelled
from katalyst.coding_agent.nodes.summarizer import get_summarization_node


# Execution-focused prompt
executor_prompt = """You are a senior software engineer implementing code changes.

Your role is to:
1. Understand the specific task assigned to you
2. Implement the solution using appropriate tools
3. Ensure the code is functional and follows best practices
4. Test your implementation when possible

Use your tools to:
- Read existing code to understand patterns (read)
- Create new files or modify existing ones (write, edit, apply_diff)
- Run commands to test functionality (bash)
- Search for relevant patterns (grep, glob)
- Request user input if critical information is missing (request_user_input)

EXECUTION GUIDELINES:
- Focus on actual implementation, not planning
- Write clean, maintainable code
- Follow existing code patterns and conventions
- Test your changes when possible
- Document complex logic with comments
- Handle errors gracefully

IMPORTANT: A task is only complete when the code is written and functional, not when you've described what to do.
"""


def executor(state: KatalystState) -> KatalystState:
    """
    Execute the current task using an executor agent with all tools.
    
    The agent will:
    - Take the current task
    - Use tools as needed
    - Return when the task is complete
    """
    logger = get_logger("coding_agent")
    logger.debug("[EXECUTOR] Starting executor node...")
    
    # Get checkpointer from manager
    checkpointer = checkpointer_manager.get_checkpointer()
    
    # Check if we have a checkpointer
    if not checkpointer:
        logger.error("[EXECUTOR] No checkpointer available from manager")
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
    
    # Get summarization node for conversation compression
    summarization_node = get_summarization_node()
    
    # Create executor agent with summarization
    executor_agent = create_react_agent(
        model=executor_model,
        tools=tools,
        checkpointer=checkpointer,
        prompt=executor_prompt,  # Set as system prompt
        pre_model_hook=summarization_node  # Enable conversation summarization
    )
    
    # Add task message to conversation
    task_message = HumanMessage(content=f"""Now, please complete this task:

Task: {current_task}

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