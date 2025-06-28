import asyncio
import inspect
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
import os
import json
import hashlib
from katalyst.coding_agent.tools.write_to_file import format_write_to_file_response

REGISTERED_TOOL_FUNCTIONS_MAP = get_tool_functions_map()


def tool_runner(state: KatalystState) -> KatalystState:
    """
    Runs the tool from state.agent_outcome (an AgentAction) and appends to action_trace.
    Handles both synchronous and asynchronous tools.

    * Primary Task: Execute the specified tool with the provided arguments.
    * State Changes:
    * Retrieves tool_name and tool_input_dict from state.agent_outcome.
    * Looks up and calls the tool function from your TOOL_REGISTRY, passing auto_approve and other necessary context.
    * Captures the observation_string (tool's return value, or an error string if the tool fails).
    * Appends the tuple (state.agent_outcome, observation_string) to state.action_trace.
    * Clears state.agent_outcome = None (as the action has been processed).
    * If the tool execution itself caused an error that should immediately halt this ReAct sub-task or even the P-n-E loop, it could set state.error_message or even state.response. (Usually, tool errors become observations for the next agent_react step).
    * Returns: The updated KatalystState.
    """
    logger = get_logger()

    # Only run if agent_outcome is an AgentAction (otherwise skip)
    agent_action = state.agent_outcome
    if not isinstance(agent_action, AgentAction):
        logger.warning(
            "[TOOL_RUNNER] No AgentAction found in state.agent_outcome. Skipping tool execution."
        )
        return state

    # Extract tool name and input arguments from the AgentAction
    tool_name = agent_action.tool
    tool_input = agent_action.tool_input or {}
    
    # Log tool execution (important for debugging)
    logger.info(f"[TOOL_RUNNER] Executing tool: {tool_name}")

    # Check for known hallucinated tools first
    if tool_name in ["multi_tool_use.parallel", "functions.AgentReactOutput"]:
        observation = create_error_message(
            ErrorType.TOOL_ERROR,
            f"Invalid tool '{tool_name}'. This appears to be a hallucinated tool name. Use only the tools explicitly listed in the available tools section.",
            "TOOL_RUNNER",
        )
        logger.warning(f"[TOOL_RUNNER] Blocked hallucinated tool: {tool_name}")
        state.error_message = observation
        state.action_trace.append((agent_action, str(observation)))
        state.agent_outcome = None
        return state
    
    # Check for repetitive tool calls
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
        return state
    
    # Look up the tool function in the registry
    tool_fn = REGISTERED_TOOL_FUNCTIONS_MAP.get(tool_name)
    if not tool_fn:
        # Tool not found: record error and skip execution
        observation = create_error_message(
            ErrorType.TOOL_ERROR,
            f"Tool '{tool_name}' not found in registry.",
            "TOOL_RUNNER",
        )
        logger.error(f"[TOOL_RUNNER] {observation}")
        state.error_message = observation
    else:
        try:
            # Prepare tool input
            if "auto_approve" in tool_fn.__code__.co_varnames:
                tool_input = {**tool_input, "auto_approve": state.auto_approve}

            tool_input_resolved = dict(tool_input)
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
            
            # Handle content_ref resolution for write_to_file
            if tool_name == "write_to_file":
                if "content_ref" in tool_input_resolved:
                    # Log that LLM chose to use content_ref
                    logger.info("[TOOL_RUNNER][CONTENT_REF] LLM chose to use content reference for write_to_file")
                else:
                    # Log that LLM provided content directly
                    content_len = len(tool_input_resolved.get("content", ""))
                    logger.info(f"[TOOL_RUNNER][CONTENT_REF] LLM provided content directly ({content_len} chars) for write_to_file")
            
            if tool_name == "write_to_file" and "content_ref" in tool_input_resolved:
                content_ref = tool_input_resolved.get("content_ref")
                logger.info(f"[TOOL_RUNNER][CONTENT_REF] write_to_file requested with content_ref: '{content_ref}'")
                
                if content_ref and content_ref in state.content_store:
                    # Replace content_ref with actual content
                    stored_data = state.content_store[content_ref]
                    # Handle both old format (string) and new format (tuple)
                    if isinstance(stored_data, tuple):
                        _, resolved_content = stored_data
                    else:
                        resolved_content = stored_data
                    
                    # Check if content was also provided (content_ref takes precedence)
                    if "content" in tool_input_resolved:
                        original_len = len(tool_input_resolved.get("content", ""))
                        logger.warning(f"[TOOL_RUNNER][CONTENT_REF] Both content ({original_len} chars) and content_ref provided. Using content_ref (precedence).")
                    
                    tool_input_resolved["content"] = resolved_content
                    # Remove content_ref from input since we've resolved it
                    del tool_input_resolved["content_ref"]
                    
                    logger.info(f"[TOOL_RUNNER][CONTENT_REF] Successfully resolved content_ref '{content_ref}' to {len(resolved_content)} chars")
                elif content_ref:
                    # Invalid reference - try to auto-correct by matching file path
                    logger.error(f"[TOOL_RUNNER][CONTENT_REF] Invalid content reference: '{content_ref}' not found in store")
                    
                    # Try to find a reference for the same file
                    corrected_ref = None
                    if ":" in content_ref:
                        # Extract file name from the invalid ref
                        parts = content_ref.split(":")
                        if len(parts) >= 2:
                            target_filename = parts[1]
                            for ref, (file_path, _) in state.content_store.items():
                                if os.path.basename(file_path) == target_filename:
                                    corrected_ref = ref
                                    logger.info(f"[TOOL_RUNNER][CONTENT_REF] Auto-correcting ref from '{content_ref}' to '{corrected_ref}' for file '{target_filename}'")
                                    break
                    
                    if corrected_ref:
                        # Use the corrected reference
                        stored_data = state.content_store[corrected_ref]
                        # Handle both old format (string) and new format (tuple)
                        if isinstance(stored_data, tuple):
                            _, resolved_content = stored_data
                        else:
                            resolved_content = stored_data
                        tool_input_resolved["content"] = resolved_content
                        del tool_input_resolved["content_ref"]
                        logger.info(f"[TOOL_RUNNER][CONTENT_REF] Successfully resolved auto-corrected ref '{corrected_ref}' to {len(resolved_content)} chars")
                    else:
                        # No correction possible
                        observation = format_write_to_file_response(
                            False,
                            tool_input_resolved.get("path", ""),
                            error=f"Invalid content reference: {content_ref}"
                        )
                        state.action_trace.append((agent_action, str(observation)))
                        state.agent_outcome = None
                        return state
                else:
                    logger.warning("[TOOL_RUNNER][CONTENT_REF] write_to_file has empty content_ref")

            # Check if the tool is an async function
            if inspect.iscoroutinefunction(tool_fn):
                # If it's async, run it in an event loop
                observation = asyncio.run(tool_fn(**tool_input_resolved))
            else:
                # Otherwise, call it directly
                observation = tool_fn(**tool_input_resolved)

            # Handle content reference system for read_file tool
            if tool_name == "read_file" and isinstance(observation, str):
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
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"[TOOL_RUNNER][CONTENT_REF] Could not process read_file observation: {e}")
            
            # The observation for generate_directory_overview is a dict, convert to JSON string
            elif isinstance(observation, dict):
                observation = json.dumps(observation, indent=2)
            
            # Handle create_subtask tool specially - modify the task queue
            if tool_name == "create_subtask" and isinstance(observation, str):
                try:
                    obs_data = json.loads(observation)
                    if obs_data.get("success"):
                        # Extract task details
                        task_description = tool_input_resolved.get("task_description", "")
                        insert_position = tool_input_resolved.get("insert_position", "after_current")
                        
                        # Check if we haven't exceeded the limit for this task
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
                        else:
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

        except GraphRecursionError as e:
            # Handle graph recursion error by triggering replanning
            error_msg = create_error_message(
                ErrorType.GRAPH_RECURSION,
                f"Graph recursion detected: {str(e)}",
                "TOOL_RUNNER",
            )
            logger.warning(f"[TOOL_RUNNER] {error_msg}")
            state.error_message = error_msg
            observation = error_msg
        except Exception as e:
            # Catch and log any other exceptions during tool execution
            observation = create_error_message(
                ErrorType.TOOL_ERROR,
                f"Exception while running tool '{tool_name}': {e}",
                "TOOL_RUNNER",
            )
            logger.exception(f"[TOOL_RUNNER] {observation}")
            state.error_message = observation

    # Record the (AgentAction, observation) tuple in the action trace
    state.action_trace.append(
        (agent_action, str(observation))
    )  # Ensure observation is a string
    logger.debug(f"[TOOL_RUNNER] Tool '{tool_name}' observation: {str(observation)}...")
    # Clear agent_outcome after processing
    state.agent_outcome = None

    return state
