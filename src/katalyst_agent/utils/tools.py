# src/katalyst_agent/utils/tools.py
import os
import importlib
from typing import List, Tuple, Dict
import inspect
import tempfile

# Directory containing all tool modules
TOOLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")

def katalyst_tool(func):
    """Decorator to mark a function as a Katalyst tool."""
    func._is_katalyst_tool = True
    return func

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
    for filename in os.listdir(TOOLS_DIR):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = f"katalyst_agent.tools.{filename[:-3]}"
            module = importlib.import_module(module_name)
            for attr in dir(module):
                func = getattr(module, attr)
                if callable(func) and getattr(func, "_is_katalyst_tool", False):
                    tool_names.append(attr)
                    sig = inspect.signature(func)
                    params = [param.name for param in sig.parameters.values() if param.name != "self"]
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
    for filename in os.listdir(TOOLS_DIR):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = f"katalyst_agent.tools.{filename[:-3]}"
            module = importlib.import_module(module_name)
            for attr in dir(module):
                func = getattr(module, attr)
                if callable(func) and getattr(func, "_is_katalyst_tool", False):
                    tool_functions[attr] = func
    return tool_functions

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
 