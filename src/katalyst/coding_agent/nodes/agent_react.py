"""
Simplified React Agent Node - Single loop agent with todo list management.

This node:
1. Creates the persistent agent if not exists
2. Runs the agent until completion
3. Handles todo list updates via tools
"""

import asyncio
import inspect
from typing import Dict, Any
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import StructuredTool

from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.config import get_llm_config
from katalyst.katalyst_core.utils.langchain_models import get_langchain_chat_model
from katalyst.katalyst_core.utils.tools import get_tool_functions_map, extract_tool_descriptions
from katalyst.app.execution_controller import check_execution_cancelled




def agent_react(state: KatalystState) -> KatalystState:
    """
    Run the agent with todo list management capabilities.
    """
    logger = get_logger()
    
    # Check if execution was cancelled
    check_execution_cancelled("agent_react")
    
    # Create agent if not exists
    if not state.agent_executor:
        logger.info("[AGENT_REACT] Creating new agent executor")
        
        # Get configured model
        llm_config = get_llm_config()
        model_name = llm_config.get_model_for_component("agent_react")
        provider = llm_config.get_provider()
        timeout = llm_config.get_timeout()
        api_base = llm_config.get_api_base()
        
        # Get model
        model = get_langchain_chat_model(
            model_name=model_name,
            provider=provider,
            temperature=0,
            timeout=timeout,
            api_base=api_base
        )
        
        # Get tools
        tool_functions = get_tool_functions_map()
        tool_descriptions_map = dict(extract_tool_descriptions())
        tools = []
        
        for tool_name, tool_func in tool_functions.items():
            description = tool_descriptions_map.get(tool_name, f"Tool: {tool_name}")
            
            if inspect.iscoroutinefunction(tool_func):
                # For async functions, create a sync wrapper
                def make_sync_wrapper(async_func):
                    def sync_wrapper(**kwargs):
                        return asyncio.run(async_func(**kwargs))
                    return sync_wrapper
                
                structured_tool = StructuredTool.from_function(
                    func=make_sync_wrapper(tool_func),
                    coroutine=tool_func,
                    name=tool_name,
                    description=description
                )
            else:
                structured_tool = StructuredTool.from_function(
                    func=tool_func,
                    name=tool_name,
                    description=description
                )
            tools.append(structured_tool)
        
        # Create agent with enhanced system prompt
        system_prompt = """You are a senior software engineer working on a coding task.

IMPORTANT INSTRUCTIONS:
1. When you receive a new task, start by using the 'create_todo_list' tool to break it down into manageable steps
2. Use the 'update_todo_list' tool to track your progress as you work
3. Work through each todo item systematically
4. When you complete the entire task, use the 'attempt_completion' tool

WORKFLOW:
1. Create a todo list for the task
2. Work through each item, marking them complete as you go
3. Add new todos if you discover additional work needed
4. Use attempt_completion when everything is done

Remember: You have access to all the tools you need to complete any coding task. Be thorough and implement actual working code."""
        
        # Add system message to conversation
        if not state.messages or not any("create_todo_list" in msg.content for msg in state.messages if hasattr(msg, 'content')):
            state.messages.insert(0, HumanMessage(content=system_prompt))
        
        # Create the agent
        state.agent_executor = create_react_agent(
            model=model,
            tools=tools,
            checkpointer=state.checkpointer if hasattr(state, 'checkpointer') else False
        )
    
    # Add the main task to the conversation
    if not any(state.task in msg.content for msg in state.messages if hasattr(msg, 'content')):
        task_message = HumanMessage(content=f"""Please complete the following task:

{state.task}

Start by creating a todo list for this task, then work through it systematically.""")
        state.messages.append(task_message)
    
    try:
        # Run the agent
        logger.info("[AGENT_REACT] Starting agent execution")
        state.agent_cycles += 1
        
        # Check cycle limit
        if state.agent_cycles >= state.max_agent_cycles:
            logger.warning(f"[AGENT_REACT] Reached max cycles ({state.max_agent_cycles})")
            state.error_message = f"Agent reached maximum cycle limit ({state.max_agent_cycles})"
            state.completion_status = "max_cycles_reached"
            return state
        
        # Invoke the agent
        result = state.agent_executor.invoke({"messages": state.messages})
        
        # Update messages
        state.messages = result.get("messages", state.messages)
        
        # Check if we should continue or stop
        if state.completion_status != "completed" and state.agent_cycles < state.max_agent_cycles:
            # Agent will continue in next cycle
            logger.debug(f"[AGENT_REACT] Agent continuing, cycle {state.agent_cycles}")
        else:
            # Agent completed or hit limit
            logger.info(f"[AGENT_REACT] Agent finished with status: {state.completion_status}")
            
            # Set final response
            if state.completion_status == "completed":
                # Get the response from attempt_completion tool
                for msg in reversed(state.messages):
                    if hasattr(msg, 'content') and 'attempt_completion' in msg.content:
                        state.response = msg.content
                        break
                    
            # Update tool execution history from messages
            for msg in state.messages:
                if hasattr(msg, 'name') and hasattr(msg, 'content'):
                    # This is a tool message
                    state.tool_execution_history.append({
                        "tool_name": msg.name,
                        "status": "success" if "error" not in msg.content.lower() else "error",
                        "summary": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                    })
                    
                    # Check if attempt_completion was called
                    if msg.name == "attempt_completion" and "success" in msg.content:
                        state.completion_status = "completed"
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[AGENT_REACT] Error during execution: {error_msg}")
        state.error_message = f"Agent execution error: {error_msg}"
        state.completion_status = "error"
    
    return state