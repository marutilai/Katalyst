import os
import subprocess
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import katalyst_tool
from shutil import which
from katalyst.app.config import SEARCH_FILES_MAX_RESULTS  # Centralized config
import json


@katalyst_tool(prompt_module="grep", prompt_var="GREP_TOOL_PROMPT", categories=["planner", "executor"])
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

    # If no matches are found, try smart variations
    if not output:
        logger.debug(f"No matches for '{pattern}', trying variations...")
        attempted_patterns = [pattern]
        
        # Try case-insensitive if not already
        if not case_insensitive:
            logger.debug("Trying case-insensitive search...")
            cmd_retry = cmd.copy()
            if "-i" not in cmd_retry:
                cmd_retry.insert(2, "-i")
            
            result_retry = subprocess.run(cmd_retry, capture_output=True, text=True, check=False)
            if result_retry.stdout.strip():
                output = result_retry.stdout.strip()
                attempted_patterns.append(f"{pattern} (case-insensitive)")
                logger.debug(f"Found matches with case-insensitive search")
            
        # If still no matches, try pattern variations
        if not output:
            variations = []
            
            # Try word boundaries
            if not pattern.startswith("\\b") and not pattern.endswith("\\b"):
                variations.append(f"\\b{pattern}\\b")
            
            # Try partial matches - split camelCase or snake_case
            import re
            # Split camelCase
            camel_parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)', pattern)
            if len(camel_parts) > 1:
                variations.append(".*".join(camel_parts))
                variations.append(".*".join(camel_parts).lower())
            
            # Split snake_case or kebab-case
            snake_parts = re.split(r'[_-]', pattern)
            if len(snake_parts) > 1:
                variations.append(".*".join(snake_parts))
            
            # Try flexible spacing patterns
            if " " not in pattern and len(pattern) > 3:
                variations.append(f".*{pattern}.*")
                variations.append(f"{pattern}.*")
                variations.append(f".*{pattern}")
            
            # Try each variation
            for var_pattern in variations:
                if var_pattern not in attempted_patterns:
                    logger.debug(f"Trying pattern variation: {var_pattern}")
                    cmd_var = ["rg", "--with-filename", "--color", "never"]
                    if show_line_numbers:
                        cmd_var.append("--line-number")
                    cmd_var.append("-i")  # Use case-insensitive for variations
                    cmd_var.extend([var_pattern, path])
                    if file_pattern:
                        cmd_var.extend(["--glob", file_pattern])
                    cmd_var.extend(["--max-count", str(max_results)])
                    cmd_var.extend(["--context", "2", "--context-separator", "-----"])
                    cmd_var.extend([
                        "-g", "!node_modules/**",
                        "-g", "!__pycache__/**",
                        "-g", "!.env",
                        "-g", "!.git/**",
                        "-g", "!*.pyc",
                        "-g", "!.venv/**",
                        "-g", "!venv/**",
                    ])
                    
                    result_var = subprocess.run(cmd_var, capture_output=True, text=True, check=False)
                    if result_var.stdout.strip():
                        output = result_var.stdout.strip()
                        attempted_patterns.append(var_pattern)
                        logger.debug(f"Found matches with pattern: {var_pattern}")
                        break
                    else:
                        attempted_patterns.append(var_pattern)
        
        # If still no matches after all attempts
        if not output:
            return json.dumps({
                "info": f"No matches found for pattern '{pattern}' in {path}.",
                "attempted_patterns": attempted_patterns,
                "suggestions": [
                    "Try a simpler pattern or partial match",
                    "Check if the file extension filter is too restrictive",
                    "Verify the search path is correct"
                ]
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