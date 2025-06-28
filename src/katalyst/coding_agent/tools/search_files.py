import os
import subprocess
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import katalyst_tool
from shutil import which
from katalyst.app.config import SEARCH_FILES_MAX_RESULTS  # Centralized config
import json


@katalyst_tool(prompt_module="search_files", prompt_var="SEARCH_FILES_PROMPT")
def regex_search_inside_files(
    path: str, regex: str, file_pattern: str = None, auto_approve: bool = True
) -> str:
    """
    Performs a regex search across files in a directory using ripgrep (rg).
    Returns a JSON object with keys: 'matches' (list of match objects), and optionally 'info' or 'error'.
    Each match object has: 'file', 'line', 'content'.
    """
    logger = get_logger()
    logger.debug(
        f"Entered regex_search_inside_files with path: {path}, regex: {regex}, file_pattern: {file_pattern}, auto_approve: {auto_approve}"
    )

    # Check for required arguments
    if not path or not regex:
        return json.dumps({"error": "Both 'path' and 'regex' arguments are required."})

    # Check if the provided path is a valid directory
    if not os.path.isdir(path):
        return json.dumps({"error": f"Directory not found: {path}"})

    # Check if ripgrep (rg) is installed and available in PATH
    if which("rg") is None:
        return json.dumps({"error": "'rg' (ripgrep) is not installed."})

    # Build the ripgrep command
    cmd = ["rg", "--with-filename", "--line-number", "--color", "never", regex, path]
    if file_pattern:
        cmd.extend(["--glob", file_pattern])
    cmd.extend(["--max-filesize", "1M", "--max-count", str(SEARCH_FILES_MAX_RESULTS)])
    cmd.extend(["--context", "2", "--context-separator", "-----"])
    cmd.extend(
        [
            "-g",
            "!node_modules/**",
            "-g",
            "!__pycache__/**",
            "-g",
            "!.env",
            "-g",
            "!.git/**",
        ]
    )

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return json.dumps(
            {
                "error": "ripgrep (rg) is not installed. Please install it to use this tool."
            }
        )

    output = result.stdout.strip()

    # If no matches are found, return an info message
    if not output:
        return json.dumps(
            {"info": f"No matches found for pattern '{regex}' in {path}."}
        )

    matches = []
    match_count = 0
    for line in output.splitlines():
        parts = line.split(":", 2)
        if len(parts) == 3:
            fname, lineno, content = parts
            matches.append(
                {
                    "file": fname,
                    "line": int(lineno) if lineno.isdigit() else lineno,
                    "content": content,
                }
            )
            match_count += 1
            if match_count >= SEARCH_FILES_MAX_RESULTS:
                break
        # Ignore context and separator lines for JSON output
    result_json = {"matches": matches}
    if match_count >= SEARCH_FILES_MAX_RESULTS:
        result_json["info"] = (
            f"Results truncated at {SEARCH_FILES_MAX_RESULTS} matches."
        )
    logger.debug("Exiting regex_search_inside_files")
    return json.dumps(result_json)
