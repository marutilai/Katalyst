import os
import json
from typing import List, Dict
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import katalyst_tool
from katalyst.katalyst_core.utils.syntax_checker import check_syntax


@katalyst_tool(prompt_module="multiedit", prompt_var="MULTIEDIT_TOOL_PROMPT", categories=["executor"])
def multiedit(
    file_path: str,
    edits: List[Dict[str, str]],
    auto_approve: bool = True
) -> str:
    """
    Apply multiple string replacements to a file.
    
    Args:
        file_path: Path to file to edit
        edits: List of dicts with 'old_string' and 'new_string'
        
    Returns:
        JSON with success status and details
    """
    logger = get_logger()
    logger.debug(f"[TOOL] Entering multiedit with file_path='{file_path}', {len(edits)} edits")
    
    # Validate inputs
    if not file_path:
        return json.dumps({"success": False, "error": "No file_path provided."})
    
    if not edits:
        return json.dumps({"success": False, "error": "No edits provided."})
    
    # Check file exists
    if not os.path.exists(file_path):
        return json.dumps({"success": False, "error": f"File not found: {file_path}"})
    
    # Read file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return json.dumps({"success": False, "error": f"Error reading file: {str(e)}"})
    
    # Validate all edits first
    for i, edit in enumerate(edits):
        if not isinstance(edit, dict):
            return json.dumps({
                "success": False, 
                "error": f"Edit {i+1} is not a dict"
            })
        
        if 'old_string' not in edit:
            return json.dumps({
                "success": False,
                "error": f"Edit {i+1} missing 'old_string'"
            })
            
        if 'new_string' not in edit:
            return json.dumps({
                "success": False,
                "error": f"Edit {i+1} missing 'new_string'"
            })
        
        if edit['old_string'] == edit['new_string']:
            return json.dumps({
                "success": False,
                "error": f"Edit {i+1} has identical old_string and new_string"
            })
            
        if edit['old_string'] not in content:
            return json.dumps({
                "success": False,
                "error": f"Edit {i+1}: String not found: {repr(edit['old_string'][:50])}"
            })
    
    # Apply edits
    new_content = content
    replacements = 0
    
    for edit in edits:
        old_string = edit['old_string']
        new_string = edit['new_string']
        
        # Count occurrences
        count = new_content.count(old_string)
        if count == 0:
            # Already checked above, but content might have changed
            continue
        
        # Replace all occurrences
        new_content = new_content.replace(old_string, new_string)
        replacements += count
        
        logger.debug(f"Replaced {count} occurrences of string")
    
    # Check syntax if applicable
    file_ext = os.path.splitext(file_path)[1].lstrip('.')
    if file_ext in ['py', 'js', 'ts', 'tsx', 'jsx']:
        syntax_error = check_syntax(new_content, file_ext)
        if syntax_error:
            return json.dumps({
                "success": False,
                "error": f"Syntax error after edits: {syntax_error}"
            })
    
    # Write file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.info(f"Successfully applied {len(edits)} edits to: {file_path}")
        return json.dumps({
            "success": True,
            "file_path": file_path,
            "info": f"Applied {len(edits)} edits, {replacements} total replacements"
        })
        
    except Exception as e:
        return json.dumps({"success": False, "error": f"Error writing file: {str(e)}"})