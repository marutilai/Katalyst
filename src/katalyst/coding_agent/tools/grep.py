import os
import subprocess
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import katalyst_tool
from shutil import which
from katalyst.app.config import SEARCH_FILES_MAX_RESULTS  # Centralized config
import json


@katalyst_tool(prompt_module="grep", prompt_var="GREP_TOOL_PROMPT")
def grep(
    pattern: str, 
    path: str = ".",
    file_pattern: str = None, 
    case_insensitive: bool = False,
    show_line_numbers: bool = True,
    max_results: int = None,
    auto_approve: bool = True
) -> str:
    """
    Search for patterns in files using ripgrep (rg).
    Returns a JSON object with keys: 'matches' (list of match objects), and optionally 'info' or 'error'.
    Each match object has: 'file', 'line', 'content'.
    """
    logger = get_logger()
    logger.debug(
        f"Entered grep with pattern: {pattern}, path: {path}, file_pattern: {file_pattern}, "
        f"case_insensitive: {case_insensitive}, show_line_numbers: {show_line_numbers}"
    )

    # Check for required arguments
    if not pattern:
        return json.dumps({"error": "Pattern is required."})

    # Use current directory if path not specified
    if not path:
        path = "."

    # Check if the provided path is valid
    if not os.path.exists(path):
        return json.dumps({"error": f"Path not found: {path}"})

    # Check if ripgrep (rg) is installed and available in PATH
    if which("rg") is None:
        return json.dumps({"error": "'rg' (ripgrep) is not installed. Please install it to use grep."})

    # Build the ripgrep command
    cmd = ["rg", "--with-filename", "--color", "never"]
    
    # Add line numbers if requested (default: True)
    if show_line_numbers:
        cmd.append("--line-number")
    
    # Add case insensitive flag if requested
    if case_insensitive:
        cmd.append("-i")
    
    # Add the pattern and path
    cmd.extend([pattern, path])
    
    # Add file pattern filter if specified
    if file_pattern:
        cmd.extend(["--glob", file_pattern])
    
    # Set max results
    if max_results is None:
        max_results = SEARCH_FILES_MAX_RESULTS
    cmd.extend(["--max-count", str(max_results)])
    
    # Add context lines for better understanding
    cmd.extend(["--context", "2", "--context-separator", "-----"])
    
    # Standard ignore patterns
    cmd.extend([
        "-g", "!node_modules/**",
        "-g", "!__pycache__/**",
        "-g", "!.env",
        "-g", "!.git/**",
        "-g", "!*.pyc",
        "-g", "!.venv/**",
        "-g", "!venv/**",
    ])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return json.dumps({
            "error": "ripgrep (rg) is not installed. Please install it to use grep."
        })

    output = result.stdout.strip()

    # If no matches are found, return an info message
    if not output:
        return json.dumps({
            "info": f"No matches found for pattern '{pattern}' in {path}."
        })

    matches = []
    match_count = 0
    for line in output.splitlines():
        # Skip context separator lines
        if line == "-----":
            continue
            
        # Parse ripgrep output format
        if show_line_numbers:
            parts = line.split(":", 2)
            if len(parts) == 3:
                fname, lineno, content = parts
                matches.append({
                    "file": fname,
                    "line": int(lineno) if lineno.isdigit() else lineno,
                    "content": content.strip(),
                })
                match_count += 1
        else:
            parts = line.split(":", 1)
            if len(parts) == 2:
                fname, content = parts
                matches.append({
                    "file": fname,
                    "content": content.strip(),
                })
                match_count += 1
                
        if match_count >= max_results:
            break
    
    result_json = {"matches": matches}
    if match_count >= max_results:
        result_json["info"] = f"Results truncated at {max_results} matches."
    
    logger.debug(f"[TOOL] Exiting grep successfully, found {len(matches)} matches")
    return json.dumps(result_json)