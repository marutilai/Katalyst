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
from collections import deque
from typing import Dict, Any, Optional, Tuple

from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import get_tool_functions_map
from katalyst.katalyst_core.utils.task_utils import find_parent_planner_task_index
from langchain_core.agents import AgentAction
from katalyst.katalyst_core.utils.error_handling import (
    ErrorType,
    create_error_message,
    classify_error,
    format_error_for_llm,
)
from langgraph.errors import GraphRecursionError
from katalyst.coding_agent.tools.write_to_file import format_write_to_file_response
from katalyst.katalyst_core.utils.directory_cache import DirectoryCache

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
        # Check if this is a consecutive duplicate
        if state.repetition_detector.is_consecutive_duplicate(tool_name, tool_input):
            # Stricter warning for back-to-back duplicates
            base_message = (
                f"⚠️ CRITICAL: Tool '{tool_name}' called with IDENTICAL inputs back-to-back! "
                "You are STUCK in a repetitive loop. THINK HARDER and CHANGE YOUR STRATEGY COMPLETELY. "
                "Stop trying the same approach. The operation context shows you ALREADY have this information. "
                "Ask yourself: What DIFFERENT tool or approach will actually progress your task?"
            )
            logger.error(f"[TOOL_RUNNER] BLOCKED CONSECUTIVE DUPLICATE: {tool_name} - This is a waste!")
        else:
            repetition_count = state.repetition_detector.get_repetition_count(tool_name, tool_input)
            base_message = (
                f"Tool '{tool_name}' has been called {repetition_count} times with identical inputs. "
                "STOP repeating the same operation! THINK HARDER about alternative approaches. "
                "What DIFFERENT tool or strategy will actually help you complete your task? "
                "Use your existing knowledge from previous operations instead of re-exploring."
            )
            logger.warning(f"[TOOL_RUNNER] Blocked repetitive tool call: {tool_name} (called {repetition_count} times)")
        
        # Add escalated feedback based on consecutive blocks
        escalation_msg = _handle_consecutive_block_escalation(tool_name, agent_action, state, logger)
        full_message = base_message + escalation_msg
        
        observation = create_error_message(
            ErrorType.TOOL_REPETITION,
            full_message,
            "TOOL_RUNNER",
        )
        state.error_message = observation
        state.action_trace.append((agent_action, str(observation)))
        state.agent_outcome = None
        return True
    
    return False


def _check_redundant_operation(tool_name: str, tool_input: Dict[str, Any], agent_action: AgentAction,
                               state: KatalystState, logger) -> bool:
    """
    Check if this operation is redundant based on recent operation context.
    
    Returns:
        True if redundant (should block), False otherwise
    """
    # Only check for read/query operations (not writes)
    read_operations = ["read_file", "list_files", "search_in_file", "search_in_directory"]
    if tool_name not in read_operations:
        return False
    
    # Check if this exact operation was recently performed successfully
    if state.operation_context.has_recent_operation(tool_name, tool_input):
        # Extract key info for better logging
        path_or_pattern = tool_input.get("path", tool_input.get("pattern", ""))
        
        base_message = (
            f"⚠️ REDUNDANT OPERATION BLOCKED: Tool '{tool_name}' was already successfully executed with these inputs. "
            "THINK HARDER - you already have this information! Check your Recent Tool Operations and action trace. "
            "Instead of re-exploring, use what you already know to make actual progress on your task. "
            "Consider: What specific action will move your task forward? Try a DIFFERENT approach."
        )
        
        # Add escalated feedback based on consecutive blocks
        escalation_msg = _handle_consecutive_block_escalation(tool_name, agent_action, state, logger)
        full_message = base_message + escalation_msg
        
        observation = create_error_message(
            ErrorType.TOOL_ERROR,
            full_message,
            "TOOL_RUNNER",
        )
        logger.warning(f"[TOOL_RUNNER] Blocked redundant operation: {tool_name} on '{path_or_pattern}' - Already have this information")
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
        # If we can't resolve paths, err on the side of caution and block the operation.
        logger.warning(f"[TOOL_RUNNER] Path validation for '{path}' failed with an exception, blocking operation")
        observation = create_error_message(
            ErrorType.TOOL_ERROR,
            f"Security error: Path validation failed for '{path}'. Could not resolve real path.",
            "TOOL_RUNNER",
        )
        state.error_message = observation
        state.action_trace.append((agent_action, str(observation)))
        state.agent_outcome = None
        return True
    
    return False


def _count_consecutive_blocks(state: KatalystState) -> int:
    """
    Count consecutive blocked operations by analyzing recent action trace.
    
    Args:
        state: Current state containing action_trace
        
    Returns:
        Number of consecutive blocked operations
    """
    consecutive_blocks = 0
    
    # Check recent action trace entries in reverse (most recent first)
    for i in range(len(state.action_trace) - 1, -1, -1):
        _, observation = state.action_trace[i]
        
        # Check if this was a blocked operation
        if any(blocked_term in str(observation) for blocked_term in [
            "BLOCKED", "REDUNDANT OPERATION", "CONSECUTIVE DUPLICATE", 
            "Tool repetition detected", "has been called"
        ]):
            consecutive_blocks += 1
        else:
            # Stop counting when we hit a successful operation
            break
    
    return consecutive_blocks


def _handle_consecutive_block_escalation(tool_name: str, agent_action: AgentAction, state: KatalystState, logger) -> str:
    """
    Analyze consecutive blocked operations and escalate feedback when agent gets stuck.
    
    Args:
        tool_name: Name of the tool that was blocked
        agent_action: The agent action that was blocked
        state: Current state containing action_trace
        logger: Logger instance
        
    Returns:
        Enhanced error message with escalated feedback if needed
    """
    # Count consecutive blocks from action trace
    consecutive_blocks = _count_consecutive_blocks(state) + 1  # +1 for the current block
    logger.debug(f"[TOOL_RUNNER] Consecutive blocks detected: {consecutive_blocks}")
    
    # Escalate feedback based on consecutive blocks
    if consecutive_blocks >= 5:
        # Very aggressive feedback after 5 consecutive blocks
        escalated_msg = (
            f"\n\n🚨 CRITICAL: You've been blocked {consecutive_blocks} times in a row! "
            "You are COMPLETELY STUCK and need to FUNDAMENTALLY CHANGE YOUR APPROACH. "
            "STOP ALL EXPLORATION and START EXECUTING your task with COMPLETELY DIFFERENT tools. "
            "Think step-by-step: What is your actual goal? What concrete action will achieve it? "
            "Use ONLY tools that make direct progress, not exploration tools."
        )
    elif consecutive_blocks >= 3:
        # Strong feedback after 3 consecutive blocks
        escalated_msg = (
            f"\n\n⚠️ WARNING: {consecutive_blocks} consecutive blocked operations! "
            "You are stuck in a repetitive pattern. CHANGE YOUR STRATEGY COMPLETELY. "
            "Stop exploring and start executing. What specific action will complete your task? "
            "Try a DIFFERENT type of tool or approach."
        )
    else:
        # Moderate escalation for first couple blocks
        escalated_msg = (
            f"\n\n💡 HINT: {consecutive_blocks} consecutive blocks. "
            "Consider if you're trying to re-do something you already accomplished. "
            "Check your action trace for existing information before exploring further."
        )
    
    return escalated_msg


# ============================================================================
# TOOL INPUT PREPARATION
# ============================================================================

def _prepare_tool_input(tool_fn, tool_input: Dict[str, Any], state: KatalystState) -> Dict[str, Any]:
    """
    Prepare tool input by adding required parameters and resolving paths.
    """
    tool_input_resolved = dict(tool_input)
    
    # Remove internal cache-related parameters that shouldn't be passed to tools
    internal_params = ["_first_call", "_original_path", "_original_recursive"]
    for param in internal_params:
        tool_input_resolved.pop(param, None)
    
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
            # Use file path as the content reference key
            content = obs_data["content"]
            file_path = obs_data.get("path", "unknown")
            
            # Store/update content with path as key (single entry)
            state.content_store[file_path] = (file_path, content)
            
            # Add path as content reference
            obs_data["content_ref"] = file_path
            observation = json.dumps(obs_data, indent=2)
            
            logger.info(f"[TOOL_RUNNER][CONTENT_REF] Stored content for '{file_path}'")
            return observation
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"[TOOL_RUNNER][CONTENT_REF] Could not process read_file observation: {e}")
    
    return observation


def _process_observation_for_trace(observation: str, tool_name: str) -> str:
    """
    Process observation before adding to action trace.
    Removes redundant content to reduce scratchpad size.
    
    Args:
        observation: Raw observation string from tool
        tool_name: Name of the tool that generated the observation
        
    Returns:
        Processed observation with redundant content removed
    """
    logger = get_logger()
    
    try:
        obs_data = json.loads(observation)
        
        # For read_file: remove content if content_ref exists
        if tool_name == "read_file" and "content_ref" in obs_data and "content" in obs_data:
            content_len = len(obs_data.get("content", ""))
            lines = obs_data.get("content", "").count('\n') + 1
            del obs_data["content"]
            obs_data["content_summary"] = f"{content_len} chars, {lines} lines"
            logger.debug(f"[PROCESS_OBS] Removed content from read_file observation, saved {content_len} chars")
            
        # For write_to_file: truncate long content
        elif tool_name == "write_to_file" and "content" in obs_data:
            content = obs_data.get("content", "")
            content_len = len(content)
            if content_len > 200:
                # Show first 100 and last 100 chars
                obs_data["content"] = content[:100] + f"\n...[{content_len-200} chars omitted]...\n" + content[-100:]
                obs_data["content_truncated"] = True
                obs_data["original_length"] = content_len
                logger.debug(f"[PROCESS_OBS] Truncated write_to_file content from {content_len} to ~200 chars")
                
        return json.dumps(obs_data, indent=2)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        # If we can't parse or process, return original
        logger.debug(f"[PROCESS_OBS] Failed to process observation for {tool_name}: {type(e).__name__}: {e}")
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
        
        # Find the parent planner task index
        parent_planner_idx = None
        if current_task_idx < len(state.task_queue):
            current_task = state.task_queue[current_task_idx]
            parent_planner_idx = find_parent_planner_task_index(
                current_task,
                current_task_idx,
                state.original_plan,
                state.created_subtasks
            )
        
        # If we couldn't find parent, use 0 as fallback
        if parent_planner_idx is None:
            parent_planner_idx = 0
            logger.warning(f"[TOOL_RUNNER] Could not determine parent planner task for subtask creation, using index 0")
        
        # Track how many subtasks created for this planner task
        if parent_planner_idx not in state.created_subtasks:
            state.created_subtasks[parent_planner_idx] = []
        
        # Check limit (5 subtasks per parent task)
        if len(state.created_subtasks[parent_planner_idx]) >= 5:
            obs_data["success"] = False
            obs_data["error"] = "Maximum subtasks (5) already created for current task"
            observation = json.dumps(obs_data)
            logger.warning(f"[TOOL_RUNNER] Subtask creation denied - limit exceeded")
            return observation
        
        # Add the subtask to the queue
        if insert_position == "after_current":
            # Count existing subtasks for this parent to insert in right position
            existing_subtasks_count = 0
            for i in range(current_task_idx + 1, len(state.task_queue)):
                task = state.task_queue[i]
                # Stop counting if we hit another planner task
                if state.original_plan and task in state.original_plan:
                    break
                existing_subtasks_count += 1
            insert_idx = current_task_idx + 1 + existing_subtasks_count
        else:  # end_of_queue
            insert_idx = len(state.task_queue)
        
        state.task_queue.insert(insert_idx, task_description)
        state.created_subtasks[parent_planner_idx].append(task_description)
        
        logger.info(f"[TOOL_RUNNER] Added subtask at position {insert_idx}: '{task_description}'")
        logger.info(f"[TOOL_RUNNER] Subtask assigned to parent planner task index {parent_planner_idx}")
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
    
    # ========== STEP 2: Check Cache for read_file and list_files ==========
    # STRIPPED DOWN: Caching logic commented out for lean implementation
    # # This must come before repetition checks to avoid blocking cached reads
    if tool_name == "read_file":
        file_path = tool_input.get("path")
        if file_path:
            # Prepare the resolved path
            if not os.path.isabs(file_path):
                resolved_path = os.path.abspath(os.path.join(state.project_root_cwd, file_path))
            else:
                resolved_path = os.path.abspath(file_path)
            
            # Check if content is cached
            if resolved_path in state.content_store:
                # Retrieve cached content
                _, cached_content = state.content_store[resolved_path]
                
                # Create observation in the same format as read_file tool
                observation = {
                    "path": resolved_path,
                    "content": cached_content,
                    "start_line": 1,
                    "end_line": len(cached_content.splitlines()),
                    "cached": True,
                    "message": "Content retrieved from cache",
                    "content_ref": resolved_path  # Include content_ref for consistency
                }
                
                # Track as successful read operation
                state.operation_context.add_file_operation(
                    file_path=resolved_path,
                    operation="read"
                )
                state.operation_context.add_tool_operation(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    success=True,
                    summary=resolved_path
                )
                
                logger.info(f"[TOOL_RUNNER][CACHE_HIT] Returned cached content for {file_path}")
                logger.debug(f"[TOOL_RUNNER] Added cached read to operation context: {resolved_path}")
                
                # Convert to JSON string like regular observations
                observation_str = json.dumps(observation, indent=2)
                
                # Process and record the observation
                # COMMENTED OUT: LangGraph manages context internally
                # processed_observation = _process_observation_for_trace(observation_str, tool_name)
                processed_observation = observation_str
                state.action_trace.append((agent_action, processed_observation))
                
                # # Keep only recent entries
                # # COMMENTED OUT: LangGraph manages its own message history
                # if len(state.action_trace) > 10:
                #     state.action_trace = state.action_trace[-10:]
                
                # Clear agent_outcome and return
                state.agent_outcome = None
                return state
    
    # Check Cache for list_files
    if tool_name == "list_files":
        # Initialize directory cache if needed
        if state.directory_cache is None:
            state.directory_cache = DirectoryCache(state.project_root_cwd).to_dict()
            logger.info("[TOOL_RUNNER][CACHE] Initialized directory cache")
        
        # Convert from dict if needed
        cache_dict = state.directory_cache
        cache = DirectoryCache.from_dict(cache_dict)
        
        # Check if we have a full scan done
        if cache.full_scan_done:
            # Serve from cache
            path = tool_input.get("path", ".")
            recursive = tool_input.get("recursive", False)
            
            # Resolve path
            if not os.path.isabs(path):
                resolved_path = os.path.abspath(os.path.join(state.project_root_cwd, path))
            else:
                resolved_path = os.path.abspath(path)
            
            # Get from cache
            cached_files = cache.get_listing(resolved_path, recursive)
            
            if cached_files is not None:
                # Create observation in list_files format
                observation = {
                    "path": resolved_path,
                    "files": cached_files,
                    "cached": True,
                    "message": "Content retrieved from directory cache"
                }
                
                # Track successful operation
                state.operation_context.add_tool_operation(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    success=True,
                    summary=f"{resolved_path} ({len(cached_files)} entries)"
                )
                
                logger.info(f"[TOOL_RUNNER][CACHE_HIT] Returned cached listing for {path}")
                
                # Convert to JSON string
                observation_str = json.dumps(observation, indent=2)
                
                # Record and return
                state.action_trace.append((agent_action, observation_str))
                
                # Keep only recent entries
                if len(state.action_trace) > 10:
                    state.action_trace = state.action_trace[-10:]
                
                # Clear agent_outcome and return
                state.agent_outcome = None
                return state
            else:
                logger.debug(f"[TOOL_RUNNER][CACHE_MISS] Path {path} not in cache")
        else:
            # First call - will trigger full scan below
            logger.info("[TOOL_RUNNER][CACHE] First list_files call, will trigger full scan")
            # Store original parameters for later
            original_path = tool_input.get("path", ".")
            original_recursive = tool_input.get("recursive", False)
            # Modify tool_input to scan from root on first call
            tool_input = dict(tool_input)
            tool_input["_first_call"] = True
            tool_input["_original_path"] = original_path
            tool_input["_original_recursive"] = original_recursive
            # Force recursive scan from root
            tool_input["path"] = state.project_root_cwd
            tool_input["recursive"] = True
    
    # ========== STEP 3: Pre-execution Validation ==========
    # STRIPPED DOWN: All validation checks commented out for lean implementation
    # We'll add these back one by one as needed
    
    # # Check for hallucinated tools
    # if _check_hallucinated_tools(tool_name, agent_action, state, logger):
    #     return state
    
    # # Check for repetitive calls
    # if _check_repetitive_calls(tool_name, tool_input, agent_action, state, logger):
    #     return state
    
    # # Check for redundant operations (deterministic state tracking)
    # if _check_redundant_operation(tool_name, tool_input, agent_action, state, logger):
    #     return state
    
    # # Validate file paths for security
    # if _validate_file_path(tool_name, tool_input, agent_action, state, logger):
    #     return state
    
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
                # Track file read operation
                try:
                    obs_data = json.loads(observation)
                    if obs_data.get("success") and "path" in obs_data:
                        state.operation_context.add_file_operation(
                            file_path=obs_data["path"],
                            operation="read"
                        )
                        logger.debug(f"[TOOL_RUNNER] Added file read to operation context: {obs_data['path']}")
                except json.JSONDecodeError:
                    pass
            
            # Convert dict observations to JSON
            elif isinstance(observation, dict):
                observation = json.dumps(observation, indent=2)
            
            # Handle list_files first scan and cache update
            if tool_name == "list_files" and isinstance(observation, str):
                try:
                    obs_data = json.loads(observation)
                    if "_first_call" in tool_input and obs_data.get("files"):
                        # This was the first call - we did a full root scan
                        logger.info("[TOOL_RUNNER][CACHE] Processing first list_files scan")
                        
                        # Update the directory cache with the full scan
                        cache = DirectoryCache.from_dict(state.directory_cache)
                        cache.perform_full_scan(tool_input_resolved.get("respect_gitignore", True))
                        state.directory_cache = cache.to_dict()
                        
                        # Now get the actual requested listing from cache
                        original_path = tool_input["_original_path"]
                        original_recursive = tool_input["_original_recursive"]
                        
                        if not os.path.isabs(original_path):
                            resolved_path = os.path.abspath(os.path.join(state.project_root_cwd, original_path))
                        else:
                            resolved_path = os.path.abspath(original_path)
                        
                        cached_files = cache.get_listing(resolved_path, original_recursive)
                        
                        # Update observation to show the originally requested path
                        obs_data = {
                            "path": resolved_path,
                            "files": cached_files or [],
                            "message": "First scan completed, returning requested directory"
                        }
                        observation = json.dumps(obs_data, indent=2)
                        
                        logger.info(f"[TOOL_RUNNER][CACHE] Cache populated, returning listing for {original_path}")
                except json.JSONDecodeError:
                    pass
            
            # Handle create_subtask special logic
            if tool_name == "create_subtask" and isinstance(observation, str):
                observation = _handle_create_subtask(observation, tool_input_resolved, state, logger)
            
            # Track file write operations and update cache
            if tool_name == "write_to_file" and isinstance(observation, str):
                try:
                    obs_data = json.loads(observation)
                    if obs_data.get("success") and "path" in obs_data:
                        # Determine if file was created or modified
                        file_path = obs_data["path"]
                        operation = "created" if obs_data.get("created", False) else "modified"
                        state.operation_context.add_file_operation(
                            file_path=file_path,
                            operation=operation
                        )
                        logger.debug(f"[TOOL_RUNNER] Added file {operation} to operation context: {file_path}")
                        
                        # Update cache with the new content
                        content = tool_input_resolved.get("content", "")
                        if content:
                            state.content_store[file_path] = (file_path, content)
                            logger.debug(f"[TOOL_RUNNER][CACHE] Updated cached content for {operation} file: {file_path} ({len(content)} chars)")
                        
                        # Update directory cache for file operations
                        if state.directory_cache:
                            cache = DirectoryCache.from_dict(state.directory_cache)
                            cache.update_for_file_operation(file_path, operation)
                            
                            # If file was created, also ensure parent directories are in cache
                            if operation == "created":
                                dir_path = os.path.dirname(file_path)
                                # Walk up the directory tree and ensure all dirs are cached
                                while dir_path and dir_path != os.path.dirname(dir_path):
                                    if not os.path.isabs(dir_path):
                                        abs_dir_path = os.path.abspath(dir_path)
                                    else:
                                        abs_dir_path = dir_path
                                    
                                    if abs_dir_path not in cache.cache:
                                        cache.update_for_directory_creation(abs_dir_path)
                                        logger.debug(f"[TOOL_RUNNER][DIR_CACHE] Added new directory to cache: {abs_dir_path}")
                                    
                                    dir_path = os.path.dirname(dir_path)
                            
                            state.directory_cache = cache.to_dict()
                            logger.debug(f"[TOOL_RUNNER][DIR_CACHE] Updated directory cache for {operation} file: {file_path}")
                except json.JSONDecodeError:
                    pass
            
            # Track apply_source_code_diff operations and update cache
            if tool_name == "apply_source_code_diff" and isinstance(observation, str):
                try:
                    obs_data = json.loads(observation)
                    if obs_data.get("success") and "path" in obs_data:
                        file_path = obs_data["path"]
                        state.operation_context.add_file_operation(
                            file_path=file_path,
                            operation="modified"
                        )
                        
                        # Read the file to update cache with new content
                        try:
                            logger.debug(f"[TOOL_RUNNER][CACHE] Reading modified file to update cache: {file_path}")
                            with open(file_path, 'r', encoding='utf-8') as f:
                                new_content = f.read()
                            state.content_store[file_path] = (file_path, new_content)
                            logger.debug(f"[TOOL_RUNNER][CACHE] Successfully updated cache for modified file: {file_path} ({len(new_content)} chars)")
                        except Exception as e:
                            # If we can't read the file, just invalidate the cache
                            if file_path in state.content_store:
                                del state.content_store[file_path]
                            logger.debug(f"[TOOL_RUNNER][CACHE] Could not read file for cache update, invalidated cache: {e}")
                        
                        # Update directory cache (file was modified)
                        if state.directory_cache:
                            cache = DirectoryCache.from_dict(state.directory_cache)
                            cache.update_for_file_operation(file_path, "modified")
                            state.directory_cache = cache.to_dict()
                            logger.debug(f"[TOOL_RUNNER][DIR_CACHE] Updated directory cache for modified file: {file_path}")
                except json.JSONDecodeError:
                    pass
            
            # Invalidate directory cache on execute_command
            if tool_name == "execute_command" and state.directory_cache:
                logger.info("[TOOL_RUNNER][DIR_CACHE] Invalidating directory cache due to execute_command")
                cache = DirectoryCache.from_dict(state.directory_cache)
                cache.invalidate()
                state.directory_cache = cache.to_dict()
                
                # Also clear operation context for list_files to allow re-scanning
                # Remove list_files operations from operation context
                filtered_ops = [
                    op for op in state.operation_context.tool_operations
                    if op.tool_name != "list_files"
                ]
                state.operation_context.tool_operations = deque(
                    filtered_ops, 
                    maxlen=state.operation_context._operations_history_limit
                )
                logger.debug("[TOOL_RUNNER][DIR_CACHE] Cleared list_files from operation context")
            
            # Track all tool operations
            success = True
            summary = None
            if isinstance(observation, str):
                try:
                    obs_data = json.loads(observation)
                    success = obs_data.get("success", True)
                    # Extract meaningful summary based on tool type
                    if tool_name == "write_to_file":
                        summary = f"{obs_data.get('path', 'unknown')}"
                    elif tool_name == "read_file":
                        summary = f"{obs_data.get('path', 'unknown')}"
                    elif tool_name == "create_subtask":
                        summary = f"Added subtask to queue"
                except json.JSONDecodeError:
                    # For non-JSON observations, check for error patterns
                    if "error" in observation.lower() or "failed" in observation.lower():
                        success = False
            
            state.operation_context.add_tool_operation(
                tool_name=tool_name,
                tool_input=tool_input_resolved,
                success=success,
                summary=summary
            )
            logger.debug(f"[TOOL_RUNNER] Added to operation context: tool={tool_name}, success={success}, summary={summary}")
            
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
    # Ensure observation is a proper string (JSON for dicts)
    if isinstance(observation, dict):
        observation_str = json.dumps(observation, indent=2)
    else:
        observation_str = str(observation)
    
    # Process observation to remove redundant content
    # COMMENTED OUT: LangGraph manages context internally, no need to truncate observations
    # processed_observation = _process_observation_for_trace(observation_str, tool_name)
    processed_observation = observation_str
    
    # # Log size reduction for debugging
    # # COMMENTED OUT: No longer processing observations
    # if len(processed_observation) < len(observation_str):
    #     reduction_pct = (1 - len(processed_observation) / len(observation_str)) * 100
    #     logger.debug(f"[TOOL_RUNNER] Observation processing reduced size by {reduction_pct:.1f}% ({len(observation_str)} -> {len(processed_observation)} chars)")
    
    state.action_trace.append((agent_action, processed_observation))
    
    # # Keep only the recent 10 entries (increased from 7 for better context)
    # # COMMENTED OUT: LangGraph manages its own message history internally
    # if len(state.action_trace) > 10:
    #     state.action_trace = state.action_trace[-10:]
    #     logger.debug(f"[TOOL_RUNNER] Trimmed action trace to keep only recent 10 entries")
    
    # Log observation size for debugging
    logger.debug(f"[TOOL_RUNNER] Tool '{tool_name}' observation: {observation_str[:200]}...")
    logger.debug(f"[TOOL_RUNNER] Observation size: {len(observation_str)} chars")
    
    # Calculate total scratchpad size
    total_scratchpad_size = sum(len(str(obs)) for _, obs in state.action_trace)
    logger.debug(f"[TOOL_RUNNER] Total scratchpad size: {total_scratchpad_size} chars across {len(state.action_trace)} actions")
    
    if total_scratchpad_size > 20000:
        logger.warning(f"[TOOL_RUNNER] Large scratchpad accumulation: {total_scratchpad_size} chars")
    
    # Clear agent_outcome after processing
    state.agent_outcome = None
    
    return state