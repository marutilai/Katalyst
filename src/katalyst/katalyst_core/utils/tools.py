# katalyst/katalyst_core/utils/tools.py
import os
import importlib
from typing import List, Tuple, Dict
import inspect
import tempfile
from typing import Callable
import re

# Directory containing all tool modules
TOOLS_IMPLEMENTATION_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "coding_agent",
    "tools",
)


def katalyst_tool(func=None, *, prompt_module=None, prompt_var=None):
    """
    Decorator to mark a function as a Katalyst tool, with optional prompt module/variable metadata.
    Usage:
        @katalyst_tool
        def foo(...): ...
    or
        @katalyst_tool(prompt_module="bar", prompt_var="BAR_PROMPT")
        def foo(...): ...
    """

    def wrapper(f):
        f._is_katalyst_tool = True
        if prompt_module:
            f._prompt_module = prompt_module
        if prompt_var:
            f._prompt_var = prompt_var
        return f

    if func is None:
        return wrapper
    return wrapper(func)


def get_tool_names_and_params() -> Tuple[List[str], List[str], Dict[str, List[str]]]:
    """
    Dynamically extract all tool function names and their argument names from the tools folder.
    Only includes functions decorated with @katalyst_tool.
    Returns:
        tool_names: List of tool function names (str)
        tool_param_names: List of all unique parameter names (str) across all tools
        tool_param_map: Dict mapping tool name to its parameter names (list of str)
    """
    tool_names = []
    tool_param_names = set()
    tool_param_map = {}
    for filename in os.listdir(TOOLS_IMPLEMENTATION_DIR):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = f"katalyst.coding_agent.tools.{filename[:-3]}"
            module = importlib.import_module(module_name)
            for attr in dir(module):
                func = getattr(module, attr)
                if callable(func) and getattr(func, "_is_katalyst_tool", False):
                    tool_names.append(attr)
                    sig = inspect.signature(func)
                    params = [
                        param.name
                        for param in sig.parameters.values()
                        if param.name != "self"
                    ]
                    tool_param_map[attr] = params
                    for param in params:
                        tool_param_names.add(param)
    return tool_names, list(tool_param_names), tool_param_map


def get_tool_functions_map() -> Dict[str, callable]:
    """
    Returns a mapping of tool function names to their function objects.
    Only includes functions decorated with @katalyst_tool.
    """
    tool_functions = {}
    if not os.path.exists(TOOLS_IMPLEMENTATION_DIR):
        print(
            f"Warning (get_tool_functions_map): Tools directory not found at {TOOLS_IMPLEMENTATION_DIR}"
        )
        return tool_functions

    for filename in os.listdir(TOOLS_IMPLEMENTATION_DIR):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = f"katalyst.coding_agent.tools.{filename[:-3]}"
            try:
                module = importlib.import_module(module_name)
                for attr_name in dir(module):
                    func_candidate = getattr(module, attr_name)
                    if callable(func_candidate) and getattr(
                        func_candidate, "_is_katalyst_tool", False
                    ):
                        # Use the stored LLM-facing tool name if available, else func name
                        tool_key = getattr(
                            func_candidate,
                            "_tool_name_for_llm_",
                            func_candidate.__name__,
                        )
                        tool_functions[tool_key] = func_candidate
            except ImportError as e:
                print(
                    f"Warning (get_tool_functions_map): Could not import module {module_name}. Error: {e}"
                )
    return tool_functions


def get_formatted_tool_prompts_for_llm(tool_functions_map: Dict[str, Callable]) -> str:
    """
    Dynamically loads and formats the detailed tool prompts for the LLM.
    Uses prompt_module and prompt_var metadata from the tool function if present, else falls back to convention.
    """
    prompt_strings = []
    for tool_function_name, func in tool_functions_map.items():
        # Use metadata if present, else fall back to convention
        prompt_module_base_name = getattr(func, "_prompt_module", tool_function_name)
        prompt_variable_name = getattr(
            func, "_prompt_var", f"{tool_function_name.upper()}_PROMPT"
        )
        try:
            module_path = (
                f"katalyst.coding_agent.prompts.tools.{prompt_module_base_name}"
            )
            module = importlib.import_module(module_path)
            if hasattr(module, prompt_variable_name):
                prompt_string = getattr(module, prompt_variable_name)
                if isinstance(prompt_string, str):
                    prompt_strings.append(prompt_string.strip())
                else:
                    print(
                        f"Warning: Prompt variable '{prompt_variable_name}' in '{module_path}' is not a string."
                    )
            else:
                print(
                    f"Warning: Prompt variable '{prompt_variable_name}' not found in '{module_path}'. Tried for tool '{tool_function_name}'."
                )
        except ImportError:
            print(
                f"Warning: Could not import prompt module '{module_path}' for tool '{tool_function_name}'."
            )
    output = "\n\n".join(prompt_strings)
    output = "You have access to the following tools:\n" + output
    return output


def extract_tool_descriptions():
    """
    Returns a list of (tool_name, one_line_description) for all registered tools.
    The description is the first line after 'Description:' in the tool's prompt file.
    """
    tool_map = get_tool_functions_map()
    tool_descriptions = []
    for tool_name, func in tool_map.items():
        prompt_module = getattr(func, "_prompt_module", tool_name)
        prompt_var = getattr(func, "_prompt_var", f"{tool_name.upper()}_PROMPT")
        try:
            module_path = f"katalyst.coding_agent.prompts.tools.{prompt_module}"
            module = importlib.import_module(module_path)
            prompt_str = getattr(module, prompt_var, None)
            if not prompt_str or not isinstance(prompt_str, str):
                continue
            # Find the first line after 'Description:'
            match = re.search(r"Description:(.*)", prompt_str)
            if match:
                desc = match.group(1).strip().split(". ")[0].strip()
                if not desc.endswith("."):
                    desc += "."
                tool_descriptions.append((tool_name, desc))
        except Exception:
            continue
    return tool_descriptions


if __name__ == "__main__":
    # Test the get_tool_names_and_params function
    tool_names, tool_params, tool_param_map = get_tool_names_and_params()
    print("Found tool names:", tool_names)
    print("Found tool parameters:", tool_params)

    # Print detailed information about each tool
    print("\nDetailed tool information:")
    for tool_name in tool_names:
        print(f"\nTool: {tool_name}")
        print(f"Parameters: {tool_param_map.get(tool_name, [])}")

    # Test get_tool_functions_map
    print("\nTesting get_tool_functions_map:")
    tool_functions = get_tool_functions_map()
    for name, func in tool_functions.items():
        print(f"Tool function: {name} -> {func}")

    # Test get_formatted_tool_prompts_for_llm
    print("\n--- TESTING FORMATTED TOOL PROMPTS FOR LLM (Dynamically Discovered) ---")
    formatted_prompts = get_formatted_tool_prompts_for_llm(tool_functions)
    if formatted_prompts:
        print(formatted_prompts)

    print("\n--- TESTING TOOL DESCRIPTIONS EXTRACTION ---")
    tool_descs = extract_tool_descriptions()
    for name, desc in tool_descs:
        print(f"- {name}: {desc}")
