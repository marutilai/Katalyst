# src/katalyst_agent/nodes/execute_tool.py
from katalyst_agent.state import KatalystAgentState
from typing import Callable, Any, Dict
import inspect
from katalyst_agent.utils.logger import get_logger
from katalyst_agent.utils.tools import get_tool_functions_map
import copy

logger = get_logger()

# Build the TOOL_REGISTRY from the functions map
TOOL_REGISTRY: Dict[str, Callable] = get_tool_functions_map()


def execute_tool(state: KatalystAgentState) -> KatalystAgentState:
    logger.info(f"Entered execute_tool (iteration {getattr(state, 'current_iteration', '?')})")
    logger.debug(f"State: {state}")
    state_before = copy.deepcopy(state)
    chat_history_before = list(state.chat_history)

    if not state.parsed_tool_call or not isinstance(state.parsed_tool_call, dict):
        logger.warning("execute_tool: No valid parsed_tool_call found in state.")
        state.tool_output = None
        state.user_feedback = None
        state.error_message = "Internal error: execute_tool was called without a parsed tool."
        changed = {k: v for k, v in state.__dict__.items() if getattr(state_before, k, None) != v}
        if "chat_history" in changed:
            del changed["chat_history"]
        if changed:
            logger.info(f"execute_tool changed state: {changed}")
        logger.info(f"Exiting execute_tool (iteration {getattr(state, 'current_iteration', '?')})")
        return state

    tool_name = state.parsed_tool_call.get("tool_name")
    tool_xml_args = state.parsed_tool_call.get("args", {})
    tool_fn = TOOL_REGISTRY.get(tool_name)

    if not tool_fn:
        logger.error(f"Tool '{tool_name}' not found in TOOL_REGISTRY.")
        state.tool_output = None
        state.user_feedback = None
        state.error_message = f"Tool '{tool_name}' not found in registry."
        state.parsed_tool_call = None
        changed = {k: v for k, v in state.__dict__.items() if getattr(state_before, k, None) != v}
        if "chat_history" in changed:
            del changed["chat_history"]
        if changed:
            logger.info(f"execute_tool changed state: {changed}")
        logger.info(f"Exiting execute_tool (iteration {getattr(state, 'current_iteration', '?')})")
        return state

    try:
        logger.info(f"Preparing to execute tool: {tool_name} with XML args: {tool_xml_args}")
        call_kwargs = {}
        sig = inspect.signature(tool_fn)
        tool_func_params = sig.parameters

        for param_name_in_signature, param_obj_in_signature in tool_func_params.items():
            if param_name_in_signature in tool_xml_args:
                xml_value_str = tool_xml_args[param_name_in_signature]
                # Type Conversion from XML string to Python type
                if param_obj_in_signature.annotation == bool:
                    call_kwargs[param_name_in_signature] = str(xml_value_str).lower() == 'true'
                elif param_obj_in_signature.annotation == int:
                    try:
                        call_kwargs[param_name_in_signature] = int(xml_value_str)
                    except ValueError:
                        logger.error(f"Type conversion error for tool '{tool_name}', param '{param_name_in_signature}'. Expected int, got '{xml_value_str}'.")
                        raise ValueError(f"Tool '{tool_name}' expected integer for parameter '{param_name_in_signature}', but received '{xml_value_str}'.")
                elif param_obj_in_signature.annotation == list and tool_name == "ask_followup_question" and param_name_in_signature == "follow_up":
                    # Special handling for ask_followup_question's 'follow_up' if it's expected as a list by the tool
                    # The XML parser gives a string of <suggest> tags. The tool needs to parse this.
                    # For now, we pass the raw string from XML. The tool itself will parse nested <suggest> tags.
                    call_kwargs[param_name_in_signature] = xml_value_str
                else:
                    call_kwargs[param_name_in_signature] = xml_value_str
            elif param_name_in_signature == 'auto_approve':
                call_kwargs['auto_approve'] = state.auto_approve

        logger.info(f"Execute tool about to call: {tool_name} with processed kwargs: {call_kwargs}")
        # All tools now return a single string
        result_string = tool_fn(**call_kwargs)
        state.tool_output = result_string

        # Check if the result_string indicates user denial to populate user_feedback for clarity
        if result_string and "[USER_DENIAL]" in result_string and "<instruction>" in result_string:
            state.user_feedback = result_string
        else:
            state.user_feedback = None

        state.error_message = None
        logger.info(f"Tool '{tool_name}' executed. Output (first 200 chars): {str(state.tool_output)[:200]}")

    except TypeError as te:
        logger.error(f"TypeError calling tool '{tool_name}'. Prepared kwargs: {call_kwargs}. XML args from LLM: {tool_xml_args}. Error: {te}")
        state.error_message = f"Error calling tool '{tool_name}': Incorrect or missing arguments expected by the tool's Python function. Details: {te}"
        state.tool_output = None
        state.user_feedback = None
    except Exception as e:
        logger.exception(f"Tool '{tool_name}' execution failed unexpectedly during call or processing.")
        state.error_message = f"Tool '{tool_name}' encountered an unexpected error during execution: {str(e)}"
        state.tool_output = None
        state.user_feedback = None

    state.parsed_tool_call = None
    changed = {k: v for k, v in state.__dict__.items() if getattr(state_before, k, None) != v}
    if "chat_history" in changed:
        del changed["chat_history"]
    if changed:
        logger.info(f"execute_tool changed state: {changed}")
    logger.info(f"Exiting execute_tool (iteration {getattr(state, 'current_iteration', '?')})")
    return state
