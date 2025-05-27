import os
import re
import importlib
from typing import Optional, Dict, Any
from katalyst_agent.utils.tools import get_tool_names_and_params

# Directory containing all tool modules
TOOLS_DIR = os.path.dirname(os.path.dirname(__file__)) + "/tools"

def parse_tool_call(assistant_message: str) -> Optional[Dict[str, Any]]:
    """
    Parses an assistant message string for XML-like tool call blocks.
    Uses tool names and parameter names from the tools folder.
    Returns:
        {tool_name: {param: value}} if a tool call is found, else {}
    """
    tool_names, _, tool_param_map = get_tool_names_and_params()
    found_tool_name = None
    tool_body_start_index = -1
    tool_body_end_index = -1
    params = {}

    # 1. Find the first complete tool call block <tool_name>...</tool_name>
    for name in tool_names:
        opening_tag = f"<{name}>"
        start_index = assistant_message.find(opening_tag)
        if start_index != -1:
            closing_tag = f"</{name}>"
            end_index = assistant_message.find(closing_tag, start_index + len(opening_tag))
            if end_index != -1:
                found_tool_name = name
                tool_body_start_index = start_index + len(opening_tag)
                tool_body_end_index = end_index
                break
    if not found_tool_name:
        return {}
    tool_body = assistant_message[tool_body_start_index:tool_body_end_index]

    # 2. Use the explicit parameter list for the tool, but also extract all <param>value</param> pairs for robustness
    param_names = tool_param_map.get(found_tool_name, [])
    # Try to extract all <param>value</param> pairs
    param_pattern = re.compile(r"<(\w+)>(.*?)</\1>", re.DOTALL)
    all_params = {m.group(1): m.group(2).strip() for m in param_pattern.finditer(tool_body)}
    # Only include those in the tool's param list, but fallback to all if param_names is empty
    if param_names:
        params = {k: v for k, v in all_params.items() if k in param_names}
    else:
        params = all_params
    return {found_tool_name: params}
 