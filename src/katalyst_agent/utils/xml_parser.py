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
    Dynamically uses tool names and parameter names from the tools folder.
    Returns:
        {tool_name: {param: value}} if a tool call is found, else {}
    """
    tool_names, tool_param_names = get_tool_names_and_params()
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
            # Search for the closing tag *after* the opening tag
            end_index = assistant_message.find(closing_tag, start_index + len(opening_tag))
            if end_index != -1:
                # Found a complete pair. Assume this is the one we want.
                found_tool_name = name
                tool_body_start_index = start_index + len(opening_tag)
                tool_body_end_index = end_index
                break  # Stop searching once the first complete tool call is found
    # 2. If no complete tool call was found, return empty dict
    if not found_tool_name:
        return {}
    # 3. Extract the content *inside* the tool tags
    tool_body = assistant_message[tool_body_start_index:tool_body_end_index]
    current_pos = 0
    # 4. Parse parameters within the tool body
    while current_pos < len(tool_body):
        found_param_in_iteration = False
        # Check if any known parameter tag starts at the current position
        for param_name in tool_param_names:
            param_opening_tag = f"<{param_name}>"
            if tool_body[current_pos:].startswith(param_opening_tag):
                param_value_start_index = current_pos + len(param_opening_tag)
                param_closing_tag = f"</{param_name}>"
                # --- Special Case: write_to_file content ---
                # Handle potential closing tags within the content itself
                if found_tool_name == "write_to_file" and param_name == "content":
                    # Find the *last* occurrence of the closing tag within the tool body,
                    # starting the search *after* the opening tag.
                    param_value_end_index = tool_body.rfind(param_closing_tag, param_value_start_index)
                else:
                    # Standard Case: Find the *first* closing tag after the opening tag.
                    param_value_end_index = tool_body.find(param_closing_tag, param_value_start_index)
                # If a valid closing tag was found for this parameter
                if param_value_end_index != -1:
                    param_value = tool_body[param_value_start_index:param_value_end_index].strip()
                    params[param_name] = param_value
                    # Move current_pos past the entire parameter block
                    current_pos = param_value_end_index + len(param_closing_tag)
                    found_param_in_iteration = True
                    break  # Found a param, restart search for the next param from the new position
                else:
                    # Found an opening tag but no closing tag before the end of the tool body.
                    # This might indicate a truncated message or invalid XML.
                    # We'll skip this broken param and continue searching after its opening tag.
                    current_pos = param_value_start_index
                    found_param_in_iteration = True
                    break  # Skip the broken param opening tag
        # If no parameter tag started at current_pos, advance by one character
        if not found_param_in_iteration:
            current_pos += 1
    return {found_tool_name: params}
