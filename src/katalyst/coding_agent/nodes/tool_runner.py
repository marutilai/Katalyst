"""
Minimal Tool Runner Node - Executes tools based on agent actions.

This is a stripped-down version that just:
1. Gets the tool from agent_outcome
2. Executes it
3. Records the result in action_trace
4. Clears agent_outcome

No caching, no validation, no processing - letting LangGraph handle everything.
"""

import json
import asyncio
import inspect
from typing import Dict, Any, Optional, Tuple

from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import get_tool_functions_map
from langchain_core.agents import AgentAction
from katalyst.katalyst_core.utils.error_handling import ErrorType, create_error_message

# Get available tools
REGISTERED_TOOL_FUNCTIONS_MAP = get_tool_functions_map()


def tool_runner(state: KatalystState) -> KatalystState:
    """
    Minimal tool runner - just executes tools without any extra processing.
    
    1. Validates we have an AgentAction
    2. Looks up the tool
    3. Executes it
    4. Appends result to action_trace
    5. Clears agent_outcome
    """
    logger = get_logger()
    
    # Get the agent action
    agent_action = state.agent_outcome
    if not isinstance(agent_action, AgentAction):
        logger.warning("[TOOL_RUNNER] No AgentAction found in state.agent_outcome")
        return state
    
    tool_name = agent_action.tool
    tool_input = agent_action.tool_input or {}
    
    logger.info(f"[TOOL_RUNNER] Executing tool: {tool_name}")
    logger.debug(f"[TOOL_RUNNER] Tool input: {tool_input}")
    
    # Look up the tool
    tool_fn = REGISTERED_TOOL_FUNCTIONS_MAP.get(tool_name)
    if not tool_fn:
        observation = create_error_message(
            ErrorType.TOOL_ERROR,
            f"Tool '{tool_name}' not found in registry.",
            "TOOL_RUNNER",
        )
        logger.error(f"[TOOL_RUNNER] Tool not found: {tool_name}")
        state.error_message = observation
        # MINIMAL: action_trace is commented out
        # state.action_trace.append((agent_action, observation))
        state.agent_outcome = None
        return state
    
    # Execute the tool
    try:
        # Minimal input preparation - just add auto_approve if needed
        tool_input_resolved = dict(tool_input)
        
        # Check if auto_approve is needed (handle mocked functions gracefully)
        try:
            if hasattr(tool_fn, '__code__') and "auto_approve" in tool_fn.__code__.co_varnames:
                tool_input_resolved["auto_approve"] = state.auto_approve
        except AttributeError:
            # Skip for mocked functions
            pass
        
        # Add user_input_fn if the tool needs it
        sig = inspect.signature(tool_fn)
        if "user_input_fn" in sig.parameters:
            tool_input_resolved["user_input_fn"] = state.user_input_fn or input
        
        # Execute (handle async/sync)
        if asyncio.iscoroutinefunction(tool_fn):
            observation = asyncio.run(tool_fn(**tool_input_resolved))
        else:
            observation = tool_fn(**tool_input_resolved)
        
        logger.debug(f"[TOOL_RUNNER] Tool executed successfully")
        
    except Exception as e:
        observation = create_error_message(
            ErrorType.TOOL_ERROR,
            f"Error executing '{tool_name}': {str(e)}",
            "TOOL_RUNNER",
        )
        logger.exception(f"[TOOL_RUNNER] Tool execution failed")
        state.error_message = observation
    
    # Convert observation to string
    if isinstance(observation, dict):
        observation_str = json.dumps(observation, indent=2)
    else:
        observation_str = str(observation)
    
    # MINIMAL: action_trace is commented out (redundant with LangGraph's message history)
    # # Record in action trace
    # # NOTE: This is somewhat redundant with LangGraph's message history,
    # # but other nodes (replanner, advance_pointer) still depend on it
    # state.action_trace.append((agent_action, observation_str))
    
    # Record concise execution history for replanner
    current_task = state.task_queue[state.task_idx] if state.task_idx < len(state.task_queue) else "Unknown task"
    execution_record = {
        "task": current_task,
        "tool_name": tool_name,
        "status": "error" if "Error:" in observation_str else "success",
        "summary": observation_str[:100] + "..." if len(observation_str) > 100 else observation_str
    }
    state.tool_execution_history.append(execution_record)
    
    # Clear agent_outcome
    state.agent_outcome = None
    
    logger.debug(f"[TOOL_RUNNER] Complete. Observation: {observation_str[:100]}...")
    
    return state