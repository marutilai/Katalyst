"""
Tool Runner Node - Executes tools based on agent actions.

This module handles the execution of tools selected by the agent, including:
- Validation of tool calls (hallucination detection, repetition detection)
- Security checks (path validation)
- Tool execution with proper error handling
- Special handling for content references and subtask creation
"""
import asyncio
import inspect
import os
import json
import hashlib
from typing import Dict, Any, Optional, Tuple

from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import get_tool_functions_map
from langchain_core.agents import AgentAction
from katalyst.katalyst_core.utils.error_handling import (
    ErrorType,
    create_error_message,
    classify_error,
    format_error_for_llm,
)
from langgraph.errors import GraphRecursionError
from katalyst.coding_agent.tools.write_to_file import format_write_to_file_response

# Global registry of available tools
REGISTERED_TOOL_FUNCTIONS_MAP = get_tool_functions_map()


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def _validate_agent_action(state: KatalystState, logger) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Validate that we have a proper AgentAction to execute.
    
    Returns:
        Tuple of (tool_name, tool_input) if valid, None otherwise
    """
    agent_action = state.agent_outcome
    if not isinstance(agent_action, AgentAction):
        logger.warning(
            "[TOOL_RUNNER] No AgentAction found in state.agent_outcome. Skipping tool execution."
        )
        return None
    
    return agent_action.tool, agent_action.tool_input or {}


def _check_hallucinated_tools(tool_name: str, agent_action: AgentAction, state: KatalystState, logger) -> bool:
    """
    Check for known hallucinated tool names that LLMs sometimes generate.
    
    Returns:
        True if tool is hallucinated (should block), False otherwise
    """
    hallucinated_tools = ["multi_tool_use.parallel", "functions.AgentReactOutput"]
    
    if tool_name in hallucinated_tools:
        observation = create_error_message(
            ErrorType.TOOL_ERROR,
            f"Invalid tool '{tool_name}'. This appears to be a hallucinated tool name. "
            "Use only the tools explicitly listed in the available tools section.",
            "TOOL_RUNNER",
        )
        logger.warning(f"[TOOL_RUNNER] Blocked hallucinated tool: {tool_name}")
        state.error_message = observation
        state.action_trace.append((agent_action, str(observation)))
        state.agent_outcome = None
        return True
    
    return False


def _check_repetitive_calls(tool_name: str, tool_input: Dict[str, Any], agent_action: AgentAction, 
                           state: KatalystState, logger) -> bool:
    """
    Check if this tool call is a repetition of recent calls.
    
    Returns:
        True if repetitive (should block), False otherwise
    """
    if not state.repetition_detector.check(tool_name, tool_input):
        repetition_count = state.repetition_detector.get_repetition_count(tool_name, tool_input)
        observation = create_error_message(
            ErrorType.TOOL_REPETITION,
            f"Tool '{tool_name}' has been called {repetition_count} times with identical inputs. "
            "Please try a different approach or tool to avoid getting stuck in a loop.",
            "TOOL_RUNNER",
        )
        logger.warning(f"[TOOL_RUNNER] Blocked repetitive tool call: {tool_name} (called {repetition_count} times)")
        state.error_message = observation
        state.action_trace.append((agent_action, str(observation)))
        state.agent_outcome = None
        return True
    
    return False


def _validate_file_path(tool_name: str, tool_input: Dict[str, Any], agent_action: AgentAction,
                       state: KatalystState, logger) -> bool:
    """
    Validate that file write operations stay within project root.
    
    Returns:
        True if path is invalid (should block), False otherwise
    """
    if tool_name not in ["write_to_file", "apply_source_code_diff"] or "path" not in tool_input:
        return False
    
    path = tool_input.get("path", "")
    if not path:
        return False
    
    # Convert to absolute path
    if not os.path.isabs(path):
        abs_path = os.path.abspath(os.path.join(state.project_root_cwd, path))
    else:
        abs_path = os.path.abspath(path)
    
    # Check if the path is within project root
    try:
        # Resolve to real paths to handle symlinks and ../ properly
        real_project_root = os.path.realpath(state.project_root_cwd)
        real_target_path = os.path.realpath(os.path.dirname(abs_path))
        
        # Ensure the target is within project root
        if not real_target_path.startswith(real_project_root):
            observation = create_error_message(
                ErrorType.TOOL_ERROR,
                f"Security error: Cannot write to '{path}' - file operations must stay within project root. "
                f"All paths should be relative to where 'katalyst' was run.",
                "TOOL_RUNNER",
            )
            logger.warning(f"[TOOL_RUNNER] Blocked file write outside project root: {abs_path}")
            state.error_message = observation
            state.action_trace.append((agent_action, str(observation)))
            state.agent_outcome = None
            return True
    except Exception as e:
        # If we can't resolve paths, err on the side of caution
        logger.warning(f"[TOOL_RUNNER] Path validation error: {e}")
    
    return False


# ============================================================================
# TOOL INPUT PREPARATION
# ============================================================================

def _prepare_tool_input(tool_fn, tool_input: Dict[str, Any], state: KatalystState) -> Dict[str, Any]:
    """
    Prepare tool input by adding required parameters and resolving paths.
    """
    tool_input_resolved = dict(tool_input)
    
    # Add auto_approve if the tool accepts it
    if "auto_approve" in tool_fn.__code__.co_varnames:
        tool_input_resolved["auto_approve"] = state.auto_approve
    
    # Resolve relative paths to absolute paths
    if (
        "path" in tool_input_resolved
        and isinstance(tool_input_resolved["path"], str)
        and not os.path.isabs(tool_input_resolved["path"])
    ):
        tool_input_resolved["path"] = os.path.abspath(
            os.path.join(state.project_root_cwd, tool_input_resolved["path"])
        )
    
    # Pass user_input_fn if the tool accepts it
    sig = inspect.signature(tool_fn)
    if "user_input_fn" in sig.parameters:
        tool_input_resolved["user_input_fn"] = state.user_input_fn or input
    
    return tool_input_resolved


# ============================================================================
# CONTENT REFERENCE HANDLING
# ============================================================================

def _handle_write_file_content_ref(tool_input_resolved: Dict[str, Any], agent_action: AgentAction,
                                  state: KatalystState, logger) -> Optional[str]:
    """
    Handle content reference resolution for write_to_file tool.
    
    Returns:
        Error observation if content ref is invalid, None otherwise
    """
    content_ref = tool_input_resolved.get("content_ref")
    
    if not content_ref:
        logger.warning("[TOOL_RUNNER][CONTENT_REF] write_to_file has empty content_ref")
        return None
    
    logger.info(f"[TOOL_RUNNER][CONTENT_REF] write_to_file requested with content_ref: '{content_ref}'")
    
    # Try to find the reference in content store
    if content_ref in state.content_store:
        # Found it - resolve the content
        stored_data = state.content_store[content_ref]
        # Handle both old format (string) and new format (tuple)
        if isinstance(stored_data, tuple):
            _, resolved_content = stored_data
        else:
            resolved_content = stored_data
        
        # Check if content was also provided (content_ref takes precedence)
        if "content" in tool_input_resolved:
            original_len = len(tool_input_resolved.get("content", ""))
            logger.warning(
                f"[TOOL_RUNNER][CONTENT_REF] Both content ({original_len} chars) and content_ref provided. "
                "Using content_ref (precedence)."
            )
        
        tool_input_resolved["content"] = resolved_content
        del tool_input_resolved["content_ref"]  # Remove since we've resolved it
        
        logger.info(
            f"[TOOL_RUNNER][CONTENT_REF] Successfully resolved content_ref '{content_ref}' "
            f"to {len(resolved_content)} chars"
        )
        return None
    
    # Not found - try to auto-correct by matching file path
    logger.error(f"[TOOL_RUNNER][CONTENT_REF] Invalid content reference: '{content_ref}' not found in store")
    
    corrected_ref = _try_autocorrect_content_ref(content_ref, state, logger)
    
    if corrected_ref:
        # Use the corrected reference
        stored_data = state.content_store[corrected_ref]
        if isinstance(stored_data, tuple):
            _, resolved_content = stored_data
        else:
            resolved_content = stored_data
        tool_input_resolved["content"] = resolved_content
        del tool_input_resolved["content_ref"]
        logger.info(
            f"[TOOL_RUNNER][CONTENT_REF] Successfully resolved auto-corrected ref '{corrected_ref}' "
            f"to {len(resolved_content)} chars"
        )
        return None
    
    # No correction possible - return error
    return format_write_to_file_response(
        False,
        tool_input_resolved.get("path", ""),
        error=f"Invalid content reference: {content_ref}"
    )


def _try_autocorrect_content_ref(content_ref: str, state: KatalystState, logger) -> Optional[str]:
    """
    Try to find a matching content reference by filename.
    """
    if ":" not in content_ref:
        return None
    
    # Extract file name from the invalid ref
    parts = content_ref.split(":")
    if len(parts) < 2:
        return None
    
    target_filename = parts[1]
    
    # Search for a reference with the same filename
    for ref, stored_data in state.content_store.items():
        if isinstance(stored_data, tuple):
            file_path, _ = stored_data
            if os.path.basename(file_path) == target_filename:
                logger.info(
                    f"[TOOL_RUNNER][CONTENT_REF] Auto-correcting ref from '{content_ref}' "
                    f"to '{ref}' for file '{target_filename}'"
                )
                return ref
    
    return None


def _create_read_file_content_ref(observation: str, state: KatalystState, logger) -> str:
    """
    Create a content reference for read_file output.
    """
    try:
        obs_data = json.loads(observation)
        if "content" in obs_data and obs_data["content"]:
            # Generate content reference ID
            content = obs_data["content"]
            content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
            file_path = obs_data.get("path", "unknown")
            ref_id = f"ref:{os.path.basename(file_path)}:{content_hash}"
            
            # Store in content_store with file path
            state.content_store[ref_id] = (file_path, content)
            
            # Add reference to observation
            obs_data["content_ref"] = ref_id
            observation = json.dumps(obs_data, indent=2)
            
            logger.info(f"[TOOL_RUNNER][CONTENT_REF] Created content reference '{ref_id}' for file '{file_path}'")
            return observation
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"[TOOL_RUNNER][CONTENT_REF] Could not process read_file observation: {e}")
    
    return observation


# ============================================================================
# SUBTASK HANDLING
# ============================================================================

def _handle_create_subtask(observation: str, tool_input_resolved: Dict[str, Any], 
                          state: KatalystState, logger) -> str:
    """
    Handle special logic for create_subtask tool - modifies the task queue.
    """
    try:
        obs_data = json.loads(observation)
        if not obs_data.get("success"):
            return observation
        
        # Extract task details
        task_description = tool_input_resolved.get("task_description", "")
        insert_position = tool_input_resolved.get("insert_position", "after_current")
        
        # Initialize created_subtasks tracking if needed
        current_task_idx = state.task_idx
        if not hasattr(state, 'created_subtasks'):
            state.created_subtasks = {}
        
        # Track how many subtasks created for current task
        if current_task_idx not in state.created_subtasks:
            state.created_subtasks[current_task_idx] = []
        
        # Check limit (5 subtasks per parent task)
        if len(state.created_subtasks[current_task_idx]) >= 5:
            obs_data["success"] = False
            obs_data["error"] = "Maximum subtasks (5) already created for current task"
            observation = json.dumps(obs_data)
            logger.warning(f"[TOOL_RUNNER] Subtask creation denied - limit exceeded")
            return observation
        
        # Add the subtask to the queue
        if insert_position == "after_current":
            insert_idx = current_task_idx + 1 + len(state.created_subtasks[current_task_idx])
        else:  # end_of_queue
            insert_idx = len(state.task_queue)
        
        state.task_queue.insert(insert_idx, task_description)
        state.created_subtasks[current_task_idx].append(task_description)
        
        logger.info(f"[TOOL_RUNNER] Added subtask at position {insert_idx}: '{task_description}'")
        logger.info(f"[TOOL_RUNNER] Updated task queue length: {len(state.task_queue)}")
        
        # Update observation to reflect success
        obs_data["message"] = f"Successfully created subtask: '{task_description}'"
        obs_data["queue_position"] = insert_idx
        observation = json.dumps(obs_data)
        
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"[TOOL_RUNNER] Failed to process create_subtask: {e}")
    
    return observation


# ============================================================================
# MAIN TOOL RUNNER FUNCTION
# ============================================================================

def tool_runner(state: KatalystState) -> KatalystState:
    """
    Runs the tool from state.agent_outcome (an AgentAction) and appends to action_trace.
    Handles both synchronous and asynchronous tools.

    Primary Task: Execute the specified tool with the provided arguments.
    
    State Changes:
    - Retrieves tool_name and tool_input from state.agent_outcome
    - Validates the tool call (hallucination, repetition, path security)
    - Executes the tool and captures the observation
    - Handles special cases (content references, subtask creation)
    - Appends (agent_outcome, observation) to state.action_trace
    - Clears state.agent_outcome = None
    
    Returns: The updated KatalystState
    """
    logger = get_logger()
    
    # ========== STEP 1: Validate Agent Action ==========
    validation_result = _validate_agent_action(state, logger)
    if not validation_result:
        return state
    
    tool_name, tool_input = validation_result
    agent_action = state.agent_outcome
    
    # Log tool execution (important for debugging)
    logger.info(f"[TOOL_RUNNER] Executing tool: {tool_name}")
    
    # ========== STEP 2: Pre-execution Validation ==========
    
    # Check for hallucinated tools
    if _check_hallucinated_tools(tool_name, agent_action, state, logger):
        return state
    
    # Check for repetitive calls
    if _check_repetitive_calls(tool_name, tool_input, agent_action, state, logger):
        return state
    
    # Validate file paths for security
    if _validate_file_path(tool_name, tool_input, agent_action, state, logger):
        return state
    
    # ========== STEP 3: Tool Lookup ==========
    tool_fn = REGISTERED_TOOL_FUNCTIONS_MAP.get(tool_name)
    if not tool_fn:
        # Tool not found in registry
        observation = create_error_message(
            ErrorType.TOOL_ERROR,
            f"Tool '{tool_name}' not found in registry.",
            "TOOL_RUNNER",
        )
        logger.error(f"[TOOL_RUNNER] {observation}")
        state.error_message = observation
    else:
        # ========== STEP 4: Tool Execution ==========
        try:
            # Prepare tool input
            tool_input_resolved = _prepare_tool_input(tool_fn, tool_input, state)
            
            # Special handling for write_to_file content references
            if tool_name == "write_to_file":
                if "content_ref" in tool_input_resolved:
                    logger.info("[TOOL_RUNNER][CONTENT_REF] LLM chose to use content reference for write_to_file")
                    error_obs = _handle_write_file_content_ref(tool_input_resolved, agent_action, state, logger)
                    if error_obs:
                        state.action_trace.append((agent_action, str(error_obs)))
                        state.agent_outcome = None
                        return state
                else:
                    content_len = len(tool_input_resolved.get("content", ""))
                    logger.info(f"[TOOL_RUNNER][CONTENT_REF] LLM provided content directly ({content_len} chars) for write_to_file")
            
            # Execute the tool (handle both sync and async)
            if inspect.iscoroutinefunction(tool_fn):
                observation = asyncio.run(tool_fn(**tool_input_resolved))
            else:
                observation = tool_fn(**tool_input_resolved)
            
            # ========== STEP 5: Post-execution Processing ==========
            
            # Create content reference for read_file
            if tool_name == "read_file" and isinstance(observation, str):
                observation = _create_read_file_content_ref(observation, state, logger)
            
            # Convert dict observations to JSON
            elif isinstance(observation, dict):
                observation = json.dumps(observation, indent=2)
            
            # Handle create_subtask special logic
            if tool_name == "create_subtask" and isinstance(observation, str):
                observation = _handle_create_subtask(observation, tool_input_resolved, state, logger)
            
        except GraphRecursionError as e:
            # Handle graph recursion error
            error_msg = create_error_message(
                ErrorType.GRAPH_RECURSION,
                f"Graph recursion detected: {str(e)}",
                "TOOL_RUNNER",
            )
            logger.warning(f"[TOOL_RUNNER] {error_msg}")
            state.error_message = error_msg
            observation = error_msg
        except Exception as e:
            # Handle any other exceptions
            observation = create_error_message(
                ErrorType.TOOL_ERROR,
                f"Exception while running tool '{tool_name}': {e}",
                "TOOL_RUNNER",
            )
            logger.exception(f"[TOOL_RUNNER] {observation}")
            state.error_message = observation
    
    # ========== STEP 6: Record Results ==========
    # Record the (AgentAction, observation) tuple in the action trace
    state.action_trace.append((agent_action, str(observation)))
    logger.debug(f"[TOOL_RUNNER] Tool '{tool_name}' observation: {str(observation)[:200]}...")
    
    # Clear agent_outcome after processing
    state.agent_outcome = None
    
    return state