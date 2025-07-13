"""
Simplified React Agent Node - Single loop agent with todo list management.

This node:
1. Creates the persistent agent if not exists
2. Runs the agent until completion
3. Handles todo list updates via tools
"""

import asyncio
import inspect
import json
from typing import Dict, Any
from langchain_core.messages import HumanMessage, ToolMessage
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
        # Check if already completed
        if state.completion_status == "completed":
            logger.info("[AGENT_REACT] ✅ Task already completed, skipping execution")
            return state
            
        # Detect if agent is stuck with attempt_completion
        recent_tool_calls = []
        for msg in reversed(state.messages[-10:]):
            if isinstance(msg, ToolMessage) and hasattr(msg, 'name'):
                recent_tool_calls.append(msg.name)
                if len(recent_tool_calls) >= 3:
                    break
        
        # If last 3 tool calls were all attempt_completion, we might be stuck
        if recent_tool_calls[:3] == ["attempt_completion"] * 3:
            logger.warning("[AGENT_REACT] ⚠️ Detected repeated attempt_completion calls - forcing completion")
            state.completion_status = "completed"
            state.error_message = "Agent stuck in completion loop - forced exit"
            return state
            
        # Run the agent
        state.agent_cycles += 1
        
        # Log current cycle
        logger.info(f"[AGENT_REACT] Cycle {state.agent_cycles}/{state.max_agent_cycles}")
        
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
        
        # Check for completion in the latest messages
        for msg in reversed(state.messages[-5:]):  # Check last 5 messages
            if hasattr(msg, 'name') and msg.name == "attempt_completion":
                # Parse the tool response to check success status
                try:
                    if isinstance(msg.content, str):
                        response_data = json.loads(msg.content)
                        if response_data.get("success", False):
                            state.completion_status = "completed"
                            logger.info("[AGENT_REACT] Task completed successfully via attempt_completion tool")
                            break
                except (json.JSONDecodeError, TypeError):
                    # If not valid JSON, check for success pattern
                    if isinstance(msg.content, str) and '"success": true' in msg.content:
                        state.completion_status = "completed"
                        logger.info("[AGENT_REACT] Task completed via attempt_completion tool")
                        break
        
        # Log the last tool call and its result
        for msg in reversed(state.messages[-6:]):
            if isinstance(msg, ToolMessage) and hasattr(msg, 'name'):
                tool_name = msg.name
                
                # Try to parse the result for better logging
                result_summary = "executed"
                try:
                    if isinstance(msg.content, str):
                        result_data = json.loads(msg.content)
                        if "message" in result_data:
                            result_summary = result_data["message"][:100] + "..." if len(result_data["message"]) > 100 else result_data["message"]
                        elif "error" in result_data:
                            result_summary = f"error: {result_data['error'][:50]}..."
                except:
                    # If not JSON, use first line of content
                    if isinstance(msg.content, str) and msg.content:
                        result_summary = msg.content.split('\n')[0][:100] + "..." if len(msg.content.split('\n')[0]) > 100 else msg.content.split('\n')[0]
                
                logger.info(f"[AGENT_REACT] Tool '{tool_name}' → {result_summary}")
                break
        
        # Check if we should continue or stop
        if state.completion_status == "completed":
            logger.info("[AGENT_REACT] ✅ Task completed successfully")
        elif state.agent_cycles >= state.max_agent_cycles:
            logger.warning(f"[AGENT_REACT] ⚠️ Reached maximum cycles limit ({state.max_agent_cycles})")
        else:
            logger.debug("[AGENT_REACT] Continuing to next cycle")
            
            # Set final response
            if state.completion_status == "completed":
                # Get the response from attempt_completion tool
                for msg in reversed(state.messages):
                    if hasattr(msg, 'content') and 'attempt_completion' in msg.content:
                        state.response = msg.content
                        break
                    
            # Update tool execution history from new messages only
            existing_tools = {(h['tool_name'], h['summary']) for h in state.tool_execution_history}
            
            # Only check recent messages to avoid duplicates
            for msg in state.messages[-10:]:
                if isinstance(msg, ToolMessage) and hasattr(msg, 'name') and hasattr(msg, 'content'):
                    # Create a meaningful summary
                    summary = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                    tool_key = (msg.name, summary)
                    
                    if tool_key not in existing_tools:
                        # Determine status from content
                        status = "success"
                        if isinstance(msg.content, str):
                            if "error" in msg.content.lower() or "failed" in msg.content.lower():
                                status = "error"
                        
                        state.tool_execution_history.append({
                            "tool_name": msg.name,
                            "status": status,
                            "summary": summary
                        })
                        existing_tools.add(tool_key)
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[AGENT_REACT] Error during execution: {error_msg}")
        state.error_message = f"Agent execution error: {error_msg}"
        state.completion_status = "error"
    
    return state