from typing import Dict
from src.katalyst_core.utils.logger import get_logger
from src.katalyst_core.utils.syntax_checker import check_syntax
from src.katalyst_core.utils.tools import katalyst_tool
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
) -> str:
    resp = {"success": success, "path": path}
    if info:
        resp["info"] = info
    if error:
        resp["error"] = error
    if cancelled:
        resp["cancelled"] = True
    return json.dumps(resp)


@katalyst_tool(prompt_module="write_to_file", prompt_var="WRITE_TO_FILE_PROMPT")
def write_to_file(path: str, content: str, auto_approve: bool = True) -> str:
    """
    Writes full content to a file, overwriting if it exists, creating it if it doesn't. Checks syntax before writing for Python files.
    Arguments:
      - path: str (file path to write)
      - content: str (the content to write)
      - auto_approve: bool (if False, ask for confirmation before writing)
    Returns a JSON string indicating success, error, or cancellation.
    """
    logger = get_logger()
    logger.info(
        f"Entered write_to_file with path={path}, content=<omitted>, auto_approve={auto_approve}"
    )

    if not path or not isinstance(path, str):
        logger.error("No valid 'path' provided to write_to_file.")
        return format_write_to_file_response(
            False, path or "", error="No valid 'path' provided."
        )
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

    # Line-numbered preview
    lines = content.split("\n")
    print(f"\n# Katalyst is about to write the following content to '{abs_path}':")
    print("-" * 80)
    for line_num, line in enumerate(lines):
        line_num_1_based = line_num + 1
        print(f"{line_num_1_based:4d} | {line}")
    print("-" * 80)

    # Confirm with user unless auto_approve is True
    if not auto_approve:
        confirm = input(f"Proceed with write to '{abs_path}'? (y/n): ").strip().lower()
        if confirm != "y":
            logger.info("User declined to write file.")
            return format_write_to_file_response(
                False, abs_path, cancelled=True, info="User declined to write file."
            )

    try:
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Successfully wrote to file: {abs_path}")
        logger.info("Exiting write_to_file")
        return format_write_to_file_response(
            True, abs_path, info=f"Successfully wrote to file: {abs_path}"
        )
    except Exception as e:
        logger.error(f"Error writing to file {abs_path}: {e}")
        logger.info("Exiting write_to_file")
        return format_write_to_file_response(
            False, abs_path, error=f"Could not write to file {abs_path}: {e}"
        )
