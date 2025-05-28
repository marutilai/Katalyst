from typing import Dict
from katalyst_agent.utils.logger import get_logger
from katalyst_agent.utils.tools import katalyst_tool
import os
import sys
import tempfile


def check_syntax(content: str, file_extension: str) -> str:
    """
    Checks syntax for the given content based on file extension.
    Currently only supports Python. Returns an error string if any, else empty string.
    TODO: Add support for other languages.
    """
    if file_extension == 'py':
        try:
            with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as tmpf:
                tmpf.write(content)
                tmpf.flush()
                tmp_path = tmpf.name
            import py_compile
            py_compile.compile(tmp_path, doraise=True)
            os.remove(tmp_path)
            return ""
        except Exception as e:
            return str(e)
    # TODO: Add general syntax checking for other languages
    return ""

@katalyst_tool
def write_to_file(path: str, content: str, mode: str, auto_approve: bool = False) -> str:
    """
    Writes full content to a file, overwriting if it exists, creating it if it doesn't. Checks syntax before writing for Python files.
    Arguments:
      - path: str (file path to write)
      - content: str (the content to write)
      - mode: str ("architect" or "code")
      - auto_approve: bool (if False, ask for confirmation before writing)
    Returns a string indicating success or error.
    """
    logger = get_logger()
    logger.info(
        f"Entered write_to_file with path={path}, content=<omitted>, mode={mode}, auto_approve={auto_approve}"
    )

    if not path or not isinstance(path, str):
        logger.error("No valid 'path' provided to write_to_file.")
        return "[ERROR] No valid 'path' provided."
    if content is None or not isinstance(content, str):
        logger.error("No valid 'content' provided to write_to_file.")
        return "[ERROR] No valid 'content' provided."

    # Architect mode restriction: only allow .md files
    if mode == "architect" and not path.endswith(".md"):
        logger.error("Architect mode: only .md files allowed.")
        return "Error: In architect mode, you are only allowed to write to markdown (.md) files."

    # Use absolute path for writing
    abs_path = os.path.abspath(path)
    file_extension = abs_path.split(".")[-1]

    # Check syntax for Python files
    errors_found = check_syntax(content, file_extension)
    if errors_found:
        logger.error(f"Syntax error: {errors_found}")
        return f"Error: Some problems were found in the content you were trying to write to '{path}'.\nHere are the problems found for '{path}':\n{errors_found}\nPlease fix the problems and try again."

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
        if confirm != 'y':
            logger.info("User declined to write file.")
            return "[CANCELLED] User declined to write file."

    try:
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(abs_path) or '.', exist_ok=True)
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Successfully wrote to file: {abs_path}")
        logger.info("Exiting write_to_file")
        return f"Successfully wrote to file: {abs_path}"
    except Exception as e:
        logger.error(f"Error writing to file {abs_path}: {e}")
        logger.info("Exiting write_to_file")
        return f"[ERROR] Could not write to file {abs_path}: {e}"

 