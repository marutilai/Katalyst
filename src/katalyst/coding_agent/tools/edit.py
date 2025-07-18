import os
import json
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import katalyst_tool
from katalyst.katalyst_core.utils.syntax_checker import check_syntax


@katalyst_tool(prompt_module="edit", prompt_var="EDIT_TOOL_PROMPT")
def edit(
    file_path: str,
    old_string: str,
    new_string: str,
    auto_approve: bool = True
) -> str:
    """
    Replace exact string in a file.
    
    Args:
        file_path: Path to file to edit
        old_string: Exact string to find and replace
        new_string: String to replace with
        
    Returns:
        JSON with success status and details
    """
    logger = get_logger()
    logger.debug(f"[TOOL] Entering edit with file_path='{file_path}'")
    
    # Validate inputs
    if not file_path:
        return json.dumps({"success": False, "error": "No file_path provided."})
    
    if old_string is None:
        return json.dumps({"success": False, "error": "No old_string provided."})
        
    if new_string is None:
        return json.dumps({"success": False, "error": "No new_string provided."})
    
    if old_string == new_string:
        return json.dumps({"success": False, "error": "old_string and new_string are identical."})
    
    # Check file exists
    if not os.path.exists(file_path):
        return json.dumps({"success": False, "error": f"File not found: {file_path}"})
    
    # Read file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return json.dumps({"success": False, "error": f"Error reading file: {str(e)}"})
    
    # Check if old_string exists
    if old_string not in content:
        return json.dumps({
            "success": False, 
            "error": f"String not found in file. Make sure to match whitespace and newlines exactly."
        })
    
    # Count occurrences
    count = content.count(old_string)
    if count > 1:
        return json.dumps({
            "success": False,
            "error": f"String found {count} times. Use MultiEdit for multiple replacements or make string more specific."
        })
    
    # Replace string
    new_content = content.replace(old_string, new_string, 1)
    
    # Check syntax if applicable
    file_ext = os.path.splitext(file_path)[1].lstrip('.')
    if file_ext in ['py', 'js', 'ts', 'tsx', 'jsx']:
        syntax_error = check_syntax(new_content, file_ext)
        if syntax_error:
            return json.dumps({
                "success": False,
                "error": f"Syntax error after edit: {syntax_error}"
            })
    
    # Write file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.info(f"Successfully edited file: {file_path}")
        return json.dumps({
            "success": True,
            "file_path": file_path,
            "info": f"Replaced 1 occurrence"
        })
        
    except Exception as e:
        return json.dumps({"success": False, "error": f"Error writing file: {str(e)}"})