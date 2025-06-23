from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import katalyst_tool
import os
from katalyst.katalyst_core.utils.file_utils import load_gitignore_patterns
import json
import hashlib


@katalyst_tool(prompt_module="read_file", prompt_var="READ_FILE_TOOL_PROMPT")
def read_file(
    path: str,
    start_line: int = 1,
    end_line: int = None,
    mode: str = "r",
    auto_approve: bool = True,
    respect_gitignore: bool = True,
) -> str:
    """
    Reads the content of a file, optionally from a specific start line to an end line (1-based, inclusive).
    Returns a JSON object with keys: 'path', 'start_line', 'end_line', 'content', and optionally 'error' or 'info'.
    """
    logger = get_logger()

    # Validate path argument
    if not path or not isinstance(path, str):
        logger.error("No valid 'path' provided to read_file.")
        return json.dumps({"error": "No valid 'path' provided."})

    abs_path = os.path.abspath(path)
    if not os.path.isfile(abs_path):
        logger.error(f"File not found: {abs_path}")
        return json.dumps({"error": f"File not found: {abs_path}"})

    # Respect .gitignore if requested (prevents reading ignored/sensitive files)
    if respect_gitignore:
        try:
            spec = load_gitignore_patterns(os.path.dirname(abs_path) or ".")
            rel_path = os.path.relpath(abs_path, os.path.dirname(abs_path) or ".")
            if spec and spec.match_file(rel_path):
                logger.error(
                    f"Permission denied to read the file '{abs_path}' due to .gitignore."
                )
                return json.dumps(
                    {
                        "error": f"Permission denied to read the file '{abs_path}' due to .gitignore."
                    }
                )
        except Exception as e:
            logger.error(f"Error loading .gitignore: {e}")
            return json.dumps({"error": f"Could not load .gitignore: {e}"})

    # --- Streaming line selection logic ---
    s_idx = (start_line - 1) if start_line and start_line > 0 else 0
    e_idx = end_line if end_line and end_line > 0 else float("inf")
    selected_lines = []
    last_line_num = s_idx
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i < s_idx:
                    continue
                if i >= e_idx:
                    break
                selected_lines.append(line)
                last_line_num = i
    except Exception as e:
        logger.error(f"Error reading file {abs_path}: {e}")
        return json.dumps({"error": f"Could not read file {abs_path}: {e}"})

    # Print preview for user (not returned to agent)
    print(f"\n# Katalyst is about to read the following content from '{abs_path}':")
    print("-" * 80)
    for idx, line in enumerate(selected_lines, start=s_idx + 1):
        print(f"{idx:4d} | {line.rstrip()}")
    print("-" * 80)


    # If no lines were selected, return an info message
    if not selected_lines:
        return json.dumps(
            {
                "path": abs_path,
                "start_line": s_idx + 1,
                "end_line": last_line_num + 1,
                "info": "File is empty or no lines in specified range.",
                "content": "",
            }
        )

    # Join selected lines for output
    file_contents = "".join(selected_lines)
    return json.dumps(
        {
            "path": abs_path,
            "start_line": s_idx + 1,
            "end_line": last_line_num + 1,
            "content": file_contents,
        }
    )
