"""
Simplified React Agent Node - Single loop agent with todo list management.

This node implements a ReAct (Reasoning + Acting) agent that:
1. Creates a persistent LangGraph agent if one doesn't exist
2. Runs the agent in a loop until task completion
3. Manages todo lists through dedicated tools (create_todo_list, update_todo_list)
4. Handles errors and prevents infinite loops
5. Tracks tool execution history for debugging

The agent maintains conversation state across multiple cycles, allowing it to
build context and work through complex tasks systematically.
"""

import json
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.config import get_llm_config
from katalyst.katalyst_core.utils.langchain_models import get_langchain_chat_model
from katalyst.katalyst_core.utils.tools import get_tool_functions_map, extract_tool_descriptions
from katalyst.katalyst_core.utils.tool_conversion import convert_tools_to_structured
from katalyst.app.execution_controller import check_execution_cancelled




def agent_react(state: KatalystState) -> KatalystState:
    """
    Main entry point for the ReAct agent node.
    
    This function:
    - Creates a persistent agent if needed
    - Runs one cycle of agent reasoning + tool execution
    - Handles completion detection and error cases
    - Updates state with results
    
    Args:
        state: Current KatalystState containing task, messages, and execution context
        
    Returns:
        Updated KatalystState with new messages, completion status, and tool history
    """
    logger = get_logger()
    
    # Check if execution was cancelled by user (e.g., Ctrl+C)
    check_execution_cancelled("agent_react")
    
    # Create agent if not exists (only happens once per conversation)
    if not state.agent_executor:
        logger.info("[AGENT_REACT] Creating new agent executor")
        
        # Get LLM configuration from environment/settings
        llm_config = get_llm_config()
        model_name = llm_config.get_model_for_component("agent_react")
        provider = llm_config.get_provider()
        timeout = llm_config.get_timeout()
        api_base = llm_config.get_api_base()
        
        # Create the LLM instance with temperature=0 for consistent outputs
        model = get_langchain_chat_model(
            model_name=model_name,
            provider=provider,
            temperature=0,
            timeout=timeout,
            api_base=api_base
        )
        
        # Load all available tools from the tools directory
        tool_functions = get_tool_functions_map()  # Dict[tool_name, function]
        tool_descriptions_map = dict(extract_tool_descriptions())  # Dict[tool_name, description]
        
        # Convert tools to StructuredTool format for LangGraph
        tools = convert_tools_to_structured(tool_functions, tool_descriptions_map)
        
        # Create agent with enhanced system prompt
        system_prompt = """You are a senior software engineer implementing production-ready solutions.

CRITICAL WORKFLOW:
1. Start by checking existing todos with 'update_todo_list' action='show'
2. If no todos exist, use 'create_todo_list' to plan your implementation
3. If todos already exist, add new tasks with 'update_todo_list' action='add'
4. Work through todos systematically - complete one before starting the next
5. Mark todos complete with 'update_todo_list' as you finish them
6. Only use 'attempt_completion' when ALL todos are done

KEY PRINCIPLES:
- Implement complete, working solutions (no placeholders or TODOs)
- Follow the project's existing patterns and conventions
- Write proper tests when implementing features
- Handle errors gracefully with meaningful messages
- If you discover additional work, add it to your todo list

COMMON PITFALLS TO AVOID:
- Don't create a new todo list without checking existing ones first
- Don't mark tasks complete until they're fully implemented
- Don't use attempt_completion if any todos remain incomplete
- Don't create files unless necessary for the task

Remember: Quality over speed. Take time to implement things properly."""
        
        # Add system prompt as first message if not already present
        # This ensures the agent understands its role and workflow
        system_prompt_exists = False
        for msg in state.messages:
            if hasattr(msg, 'content') and "create_todo_list" in msg.content:
                system_prompt_exists = True
                break
                
        if not state.messages or not system_prompt_exists:
            state.messages.insert(0, HumanMessage(content=system_prompt))
        
        # Create the persistent ReAct agent using LangGraph
        # This agent will maintain conversation state across multiple cycles
        state.agent_executor = create_react_agent(
            model=model,
            tools=tools,
            checkpointer=state.checkpointer if hasattr(state, 'checkpointer') else False
        )
    
    # Add the user's task to the conversation if not already present
    # This happens on the first cycle to kick off the agent's work
    task_already_in_messages = False
    for msg in state.messages:
        if hasattr(msg, 'content') and state.task in msg.content:
            task_already_in_messages = True
            break
            
    if not task_already_in_messages:
        task_message = HumanMessage(content=f"""Please complete the following task:

{state.task}

Start by creating a todo list for this task, then work through it systematically.""")
        state.messages.append(task_message)
    
    try:
        # Skip execution if task is already completed
        if state.completion_status == "completed":
            logger.info("[AGENT_REACT] ✅ Task already completed, skipping execution")
            return state
            
        # Simple check for repeated attempt_completion (the most common stuck pattern)
        recent_messages = state.messages[-5:]
        attempt_completion_count = 0
        for msg in reversed(recent_messages):
            if isinstance(msg, ToolMessage) and hasattr(msg, 'name') and msg.name == "attempt_completion":
                attempt_completion_count += 1
                
        if attempt_completion_count >= 3:
            logger.warning("[AGENT_REACT] Detected repeated attempt_completion - forcing exit")
            state.completion_status = "completed"
            return state
            
        # ===== EXECUTE ONE AGENT CYCLE =====
        state.agent_cycles += 1
        
        # Log progress for visibility
        logger.info(f"[AGENT_REACT] Cycle {state.agent_cycles}/{state.max_agent_cycles}")
        
        # Check if we've hit the maximum allowed cycles
        if state.agent_cycles >= state.max_agent_cycles:
            logger.warning(f"[AGENT_REACT] Reached max cycles ({state.max_agent_cycles})")
            state.error_message = f"Agent reached maximum cycle limit ({state.max_agent_cycles})"
            state.completion_status = "max_cycles_reached"
            return state
        
        # Invoke the agent
        result = state.agent_executor.invoke({"messages": state.messages})
        
        # Update messages from the result
        state.messages = result.get("messages", state.messages)
        
        # Check if attempt_completion was called successfully
        for msg in reversed(state.messages[-5:]):
            if isinstance(msg, ToolMessage) and hasattr(msg, 'name') and msg.name == "attempt_completion":
                try:
                    response_data = json.loads(msg.content)
                    if response_data.get("success", False):
                        state.completion_status = "completed"
                        state.response = response_data.get("result", "Task completed")
                        logger.info("[AGENT_REACT] Task completed successfully")
                        break
                except json.JSONDecodeError:
                    # Tool response wasn't valid JSON, let the agent retry
                    pass
        
        # ===== LOG TOOL EXECUTION FOR DEBUGGING =====
        # Find and log the most recent tool call to help with debugging
        for msg in reversed(state.messages[-6:]):
            if isinstance(msg, ToolMessage) and hasattr(msg, 'name'):
                tool_name = msg.name
                
                # Try to extract a meaningful summary from the tool response
                result_summary = "executed"
                try:
                    if isinstance(msg.content, str):
                        result_data = json.loads(msg.content)
                        if "message" in result_data:
                            # Truncate long messages for readable logs
                            result_summary = result_data["message"][:100] + "..." if len(result_data["message"]) > 100 else result_data["message"]
                        elif "error" in result_data:
                            result_summary = f"error: {result_data['error'][:50]}..."
                except (json.JSONDecodeError, TypeError):
                    # Fallback: use first line of raw content
                    if isinstance(msg.content, str) and msg.content:
                        result_summary = msg.content.split('\n')[0][:100] + "..." if len(msg.content.split('\n')[0]) > 100 else msg.content.split('\n')[0]
                
                logger.info(f"[AGENT_REACT] Tool '{tool_name}' → {result_summary}")
                break
        
        # ===== UPDATE TOOL EXECUTION HISTORY =====
        # Track all tool calls for debugging and audit trail
        existing_tools = {(h['tool_name'], h['summary']) for h in state.tool_execution_history}
        
        # Only check recent messages to avoid duplicates
        for msg in state.messages[-10:]:
            if isinstance(msg, ToolMessage) and hasattr(msg, 'name') and hasattr(msg, 'content'):
                # Create a meaningful summary
                summary = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                tool_key = (msg.name, summary)
                
                # Avoid duplicate entries
                if tool_key not in existing_tools:
                    # Determine if the tool execution was successful or not
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
        
        # Log completion status
        if state.completion_status == "completed":
            logger.info("[AGENT_REACT] ✅ Task completed successfully")
        elif state.agent_cycles >= state.max_agent_cycles:
            logger.warning(f"[AGENT_REACT] ⚠️ Reached maximum cycles limit ({state.max_agent_cycles})")
        else:
            logger.debug("[AGENT_REACT] Continuing to next cycle")
        
    except Exception as e:
        # Catch any unexpected errors and record them in state
        error_msg = str(e)
        logger.error(f"[AGENT_REACT] Error during execution: {error_msg}")
        state.error_message = f"Agent execution error: {error_msg}"
        state.completion_status = "error"
    
    # Return the updated state for the next cycle or completion
    return state