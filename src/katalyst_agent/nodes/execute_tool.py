from katalyst_agent.state import KatalystAgentState
from typing import Callable, Any, Dict, Tuple
import importlib
import sys
import os
from katalyst_agent.utils.logger import get_logger

# Map tool invocation names to (module, function_name)
TOOL_SPECS = {
    "list_files": ("list_files", "list_files"),
    "ask_followup_question": ("ask_followup_question", "ask_followup_question"),
    "list_code_definitions": ("list_code_definitions", "list_code_definition_names"),
    "read_file": ("read_file", "read_file"),
    "search_files": ("search_files", "regex_search_files"),
    "write_to_file": ("write_to_file", "write_to_file"),
    "apply_diff": ("apply_diff", "apply_diff"),
    "execute_command": ("execute_command", "execute_command"),
}

TOOL_REGISTRY: Dict[str, Callable] = {}

TOOLS_PATH = os.path.dirname(__file__).replace("nodes", "tools")
if TOOLS_PATH not in sys.path:
    sys.path.insert(0, TOOLS_PATH)

for tool_name, (module_name, func_name) in TOOL_SPECS.items():
    try:
        module = importlib.import_module(f"katalyst_agent.tools.{module_name}")
        func = getattr(module, func_name)
        TOOL_REGISTRY[tool_name] = func
    except Exception as e:
        print(f"Failed to import tool {tool_name}: {e}")


def execute_tool(state: KatalystAgentState) -> KatalystAgentState:
    logger = get_logger()
    logger.info(f"Entered execute_tool with state: {state}")
    """
    Executes the tool specified in parsed_tool_call and updates the state.
    """
    if not state.parsed_tool_call:
        state.tool_output = None
        state.user_feedback = None
        state.error_message = None
        return state

    tool_name = state.parsed_tool_call.get("tool_name")
    tool_args = state.parsed_tool_call.get("args", {})
    tool_fn = TOOL_REGISTRY.get(tool_name)

    if not tool_fn:
        state.tool_output = None
        state.user_feedback = None
        state.error_message = f"Tool '{tool_name}' not found."
        state.parsed_tool_call = None
        return state

    try:
        # Try calling with all possible signatures
        try:
            result = tool_fn(tool_args, state.current_mode, state.auto_approve)
        except TypeError:
            try:
                result = tool_fn(tool_args, state.auto_approve)
            except TypeError:
                result = tool_fn(tool_args)
        # If the tool returns a tuple, unpack it
        if isinstance(result, tuple):
            result_string_for_llm, user_feedback_string_or_none = result
        else:
            result_string_for_llm, user_feedback_string_or_none = result, None
        state.tool_output = result_string_for_llm
        state.user_feedback = user_feedback_string_or_none
        state.error_message = None
    except Exception as e:
        state.tool_output = None
        state.user_feedback = None
        state.error_message = f"Tool '{tool_name}' execution failed: {e}"
    state.parsed_tool_call = None
    logger.info(f"Exiting execute_tool with updated state.")
    return state
