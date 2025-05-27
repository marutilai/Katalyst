import os
import importlib
from typing import List, Tuple
import inspect

# Directory containing all tool modules
TOOLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")

def katalyst_tool(func):
    """Decorator to mark a function as a Katalyst tool."""
    func._is_katalyst_tool = True
    return func

def get_tool_names_and_params() -> Tuple[List[str], List[str]]:
    """
    Dynamically extract all tool function names and their argument names from the tools folder.
    Only includes functions decorated with @katalyst_tool.
    Returns:
        tool_names: List of tool function names (str)
        tool_param_names: List of all unique parameter names (str) across all tools
    """
    tool_names = []
    tool_param_names = set()
    for filename in os.listdir(TOOLS_DIR):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = f"katalyst_agent.tools.{filename[:-3]}"
            module = importlib.import_module(module_name)
            for attr in dir(module):
                func = getattr(module, attr)
                if callable(func) and getattr(func, "_is_katalyst_tool", False):
                    tool_names.append(attr)
                    sig = inspect.signature(func)
                    for param in sig.parameters.values():
                        if param.name != "self":
                            tool_param_names.add(param.name)
    return tool_names, list(tool_param_names)

if __name__ == "__main__":
    # Test the get_tool_names_and_params function
    tool_names, tool_params = get_tool_names_and_params()
    print("Found tool names:", tool_names)
    print("Found tool parameters:", tool_params)
    
    # Print detailed information about each tool
    print("\nDetailed tool information:")
    for tool_name in tool_names:
        print(f"\nTool: {tool_name}")
        print(f"Parameters: {[param for param in tool_params if param in tool_name]}")
