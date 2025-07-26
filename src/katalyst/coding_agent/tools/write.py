import os
import json
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.syntax_checker import check_syntax
from katalyst.katalyst_core.utils.tools import katalyst_tool
from katalyst.katalyst_core.utils.error_handling import create_error_message, ErrorType
from katalyst.app.ui.input_handler import InputHandler
from katalyst.app.execution_controller import check_execution_cancelled


@katalyst_tool(prompt_module="write", prompt_var="WRITE_TOOL_PROMPT", categories=["executor"])
def write(path: str, content: str, auto_approve: bool = True) -> str:
    """
    Write content to a file, creating it if it doesn't exist.
    Checks syntax before writing for supported file types.
    
    Args:
        path: File path to write to
        content: Content to write to the file
        auto_approve: Whether to skip user confirmation (default: True)
        
    Returns:
        JSON with 'success', 'path', and optionally 'error', 'created', 'info'
    """
    logger = get_logger()
    logger.debug(f"[TOOL] Entering write with path='{path}', content_length={len(content) if content else 0}")
    
    # Validate inputs
    if not path:
        return json.dumps({"success": False, "error": "No path provided."})
    
    if content is None:
        return json.dumps({"success": False, "path": path, "error": "No content provided."})
    
    # Check if trying to write CSV file
    if path.endswith('.csv'):
        error_msg = create_error_message(
            ErrorType.TOOL_ERROR,
            "CSV files should be saved using execute_data_code with df.to_csv(). Example: execute_data_code(\"df.to_csv('/path/to/file.csv', index=False)\")",
            "write"
        )
        logger.error(error_msg)
        return json.dumps({
            "success": False, 
            "path": path, 
            "error": error_msg
        })
    
    # Get file extension for syntax checking
    file_extension = os.path.splitext(path)[1].lstrip('.')
    
    # Check syntax for supported file types (Python, JavaScript, etc.)
    if file_extension:
        syntax_errors = check_syntax(content, file_extension)
        if syntax_errors:
            logger.error(f"Syntax error in {path}: {syntax_errors}")
            return json.dumps({
                "success": False,
                "path": path,
                "error": f"Syntax error: {syntax_errors}"
            })
    
    # Check if file already exists
    file_exists = os.path.exists(path)
    
    # Check if execution was cancelled
    try:
        check_execution_cancelled("write")
    except KeyboardInterrupt:
        logger.info("Write operation cancelled by user")
        return json.dumps({
            "success": False,
            "path": path,
            "cancelled": True,
            "info": "Operation cancelled by user"
        })
    
    # Handle user approval if needed
    if not auto_approve:
        input_handler = InputHandler()
        
        # Load existing content for diff if file exists
        old_content = None
        if file_exists:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    old_content = f.read()
            except:
                old_content = None
        
        # Prompt for approval
        approved = input_handler.prompt_file_approval(
            file_path=path,
            content=content,
            exists=file_exists,
            show_diff=file_exists and old_content is not None,
            old_content=old_content
        )
        
        if not approved:
            logger.info("User declined to write file")
            return json.dumps({
                "success": False,
                "path": path,
                "cancelled": True,
                "info": "User declined to write file"
            })
    else:
        # Show preview even with auto_approve for visibility
        lines = content.split('\n')
        print(f"\n# Writing to '{path}' ({len(lines)} lines)")
        
        if len(lines) <= 10:
            # Show all lines for small files
            for i, line in enumerate(lines, 1):
                print(f"{i:4d} | {line}")
        else:
            # Show first 5 and last 5 lines for large files
            for i, line in enumerate(lines[:5], 1):
                print(f"{i:4d} | {line}")
            print("     | ...")
            start = len(lines) - 4
            for i, line in enumerate(lines[-5:], start):
                print(f"{i:4d} | {line}")
    
    # Write the file
    try:
        # Create parent directory if needed
        parent_dir = os.path.dirname(path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        
        # Write content
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Successfully wrote to file: {path}")
        logger.debug(f"[TOOL] Exiting write successfully, wrote {len(content)} chars")
        
        result = {
            "success": True,
            "path": path,
            "created": not file_exists
        }
        
        if not file_exists:
            result["info"] = f"Created new file: {path}"
        else:
            result["info"] = f"Updated existing file: {path}"
            
        return json.dumps(result)
        
    except Exception as e:
        logger.error(f"Error writing to file {path}: {e}")
        return json.dumps({
            "success": False,
            "path": path,
            "error": f"Failed to write file: {str(e)}"
        })