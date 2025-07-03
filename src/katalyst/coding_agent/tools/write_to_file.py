from typing import Dict
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.syntax_checker import check_syntax
from katalyst.katalyst_core.utils.tools import katalyst_tool
from katalyst.app.ui.input_handler import InputHandler
from katalyst.app.execution_controller import check_execution_cancelled
import os
import sys
import tempfile
import json


def format_write_to_file_response(
    success: bool,
    path: str,
    info: str = None,
    error: str = None,
    cancelled: bool = False,
    created: bool = False,
) -> str:
    resp = {"success": success, "path": path}
    if info:
        resp["info"] = info
    if error:
        resp["error"] = error
    if cancelled:
        resp["cancelled"] = True
    if created:
        resp["created"] = True
    return json.dumps(resp)


@katalyst_tool(prompt_module="write_to_file", prompt_var="WRITE_TO_FILE_TOOL_PROMPT")
def write_to_file(
    path: str, content: str, auto_approve: bool = True, user_input_fn=None
) -> str:
    """
    Writes full content to a file, overwriting if it exists, creating it if it doesn't. 
    Checks syntax before writing for Python files.
    
    Arguments:
      - path: str (file path to write)
      - content: str (the content to write)
      - auto_approve: bool (if False, ask for confirmation before writing)
      - user_input_fn: function to use for user input (defaults to input)
      
    Returns a JSON string indicating success, error, or cancellation.
    """
    logger = get_logger()
    logger.debug(f"[TOOL] Entering write_to_file with path='{path}', content_length={len(content) if content else 0}, auto_approve={auto_approve}")

    if user_input_fn is None:
        user_input_fn = input

    if not path or not isinstance(path, str):
        logger.error("No valid 'path' provided to write_to_file.")
        result = format_write_to_file_response(
            False, path or "", error="No valid 'path' provided."
        )
        logger.debug(f"[TOOL] Exiting write_to_file with error: invalid path")
        return result
    if content is None or not isinstance(content, str):
        logger.error("No valid 'content' provided to write_to_file.")
        return format_write_to_file_response(
            False, path, error="No valid 'content' provided."
        )

    # Use absolute path for writing
    abs_path = os.path.abspath(path)
    file_extension = abs_path.split(".")[-1]

    # Check syntax for Python files
    errors_found = check_syntax(content, file_extension)
    if errors_found:
        logger.error(f"Syntax error: {errors_found}")
        return format_write_to_file_response(
            False,
            abs_path,
            error=f"Error: Some problems were found in the content you were trying to write to '{path}'. Here are the problems found for '{path}': {errors_found} Please fix the problems and try again.",
        )

    # Check if file exists before writing
    file_exists = os.path.exists(abs_path)
    
    # Check if execution was cancelled before proceeding
    try:
        check_execution_cancelled("write_to_file")
    except KeyboardInterrupt:
        logger.info("Write to file cancelled by user")
        return format_write_to_file_response(
            False, abs_path, cancelled=True, info="Operation cancelled by user"
        )
    
    # Use enhanced input handler for better UI
    input_handler = InputHandler()
    
    # Show preview and get approval
    if not auto_approve:
        # Load existing content if file exists
        old_content = None
        if file_exists:
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    old_content = f.read()
            except:
                old_content = None
        
        # Use enhanced file approval
        approved = input_handler.prompt_file_approval(
            file_path=abs_path,
            content=content,
            exists=file_exists,
            show_diff=file_exists and old_content is not None,
            old_content=old_content
        )
        
        if not approved:
            logger.info("User declined to write file.")
            result = format_write_to_file_response(
                False, abs_path, cancelled=True, info="User declined to write file."
            )
            logger.debug(f"[TOOL] Exiting write_to_file: user declined")
            return result
    else:
        # Even with auto_approve, show a brief preview for logging
        lines = content.split("\n")
        print(f"\n# Writing to '{abs_path}' ({len(lines)} lines)")
        if len(lines) <= 10:
            for line_num, line in enumerate(lines, 1):
                print(f"{line_num:4d} | {line}")
        else:
            # Show first 5 and last 5 lines
            for line_num, line in enumerate(lines[:5], 1):
                print(f"{line_num:4d} | {line}")
            print("     | ...")
            start_num = len(lines) - 4
            for idx, line in enumerate(lines[-5:]):
                print(f"{start_num + idx:4d} | {line}")

    try:
        
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Successfully wrote to file: {abs_path}")
        result = format_write_to_file_response(
            True, abs_path, 
            info=f"Successfully wrote to file: {abs_path}",
            created=not file_exists  # True if file didn't exist before
        )
        logger.debug(f"[TOOL] Exiting write_to_file successfully, wrote {len(content)} chars to {abs_path}")
        return result
    except Exception as e:
        logger.error(f"Error writing to file {abs_path}: {e}")
        return format_write_to_file_response(
            False, abs_path, error=f"Could not write to file {abs_path}: {e}"
        )
