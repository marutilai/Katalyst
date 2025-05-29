import re
from typing import Optional, Dict, Any
from katalyst_agent.utils.tools import get_tool_names_and_params
from katalyst_agent.utils.logger import get_logger

logger = get_logger()


def parse_tool_call(assistant_message: str) -> Optional[Dict[str, Any]]:
    """
    Parses an assistant message string for XML-like tool call blocks.
    Uses tool names and parameter names from the tools folder.
    Returns:
        {tool_name: {param: value}} if a tool call is found, else {}
    """
    tool_names, _, tool_param_map = get_tool_names_and_params()
    if not tool_names:
        logger.warning("parse_tool_call: No tool names found by get_tool_names_and_params().")
        return {}

    found_tool_name = None
    tool_body_start_index = -1
    tool_body_end_index = -1
    
    # Store potential matches with their start indices to pick the first one
    potential_matches = []

    for name in tool_names:
        opening_tag = f"<{name}>"
        start_index = assistant_message.find(opening_tag)
        if start_index != -1:
            closing_tag = f"</{name}>"
            # Search for the closing tag *after* the opening tag itself
            body_content_end_index = assistant_message.find(closing_tag, start_index + len(opening_tag))
            if body_content_end_index != -1:
                potential_matches.append({
                    "name": name,
                    "start_index": start_index, # start of <tool_name>
                    "body_start_index": start_index + len(opening_tag), # end of <tool_name>
                    "body_end_index": body_content_end_index, # start of </tool_name>
                })

    if not potential_matches:
        logger.debug(f"parse_tool_call: No tool tags found in message: {assistant_message[:200]}...")
        return {}

    # Select the earliest occurring, valid tool block
    potential_matches.sort(key=lambda m: m["start_index"])
    first_match = potential_matches[0]
    found_tool_name = first_match["name"]
    tool_body_start_index = first_match["body_start_index"]
    tool_body_end_index = first_match["body_end_index"]
    
    tool_body = assistant_message[tool_body_start_index:tool_body_end_index]
    logger.debug(f"parse_tool_call: Found tool '{found_tool_name}'. Body: {tool_body[:200]}...")

    param_names_for_tool = tool_param_map.get(found_tool_name, [])
    # Use a robust regex to find <param>value</param> within the extracted tool_body
    param_pattern = re.compile(r"<(\w+)>(.*?)</\1>", re.DOTALL)
    
    parsed_params = {}
    for match in param_pattern.finditer(tool_body):
        param_name = match.group(1)
        param_value = match.group(2).strip()
        # Only include params that are expected for the tool, if param_names_for_tool is populated
        if not param_names_for_tool or param_name in param_names_for_tool:
            parsed_params[param_name] = param_value
        else:
            logger.warning(f"parse_tool_call: Found unexpected param '{param_name}' for tool '{found_tool_name}'. Ignoring.")

    # Ensure all required params (if any defined) are present or handle defaults elsewhere
    if not parsed_params and param_names_for_tool:
        logger.warning(f"parse_tool_call: Tool '{found_tool_name}' expects params {param_names_for_tool}, but none were parsed from body: {tool_body[:200]}...")
        # Depending on strictness, one might return {} here.
        # However, some tools might have all optional params or params passed in other ways (like mode/auto_approve)
        # The original code implies that even if params are not found in XML, it proceeds.
        # Let's stick to returning the tool name if the tags are found, even if body parsing is imperfect.

    return {found_tool_name: parsed_params}
 