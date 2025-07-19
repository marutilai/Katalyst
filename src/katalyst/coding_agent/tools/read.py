import os
import json
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import katalyst_tool
from katalyst.katalyst_core.utils.file_utils import load_gitignore_patterns


@katalyst_tool(prompt_module="read", prompt_var="READ_TOOL_PROMPT", categories=["planner", "executor", "replanner"])
def read(
    path: str,
    start_line: int = None,
    end_line: int = None,
    respect_gitignore: bool = True,
    auto_approve: bool = True
) -> str:
    """
    Read the contents of a file, optionally from a specific line range.
    
    Args:
        path: File path to read
        start_line: Starting line number (1-based, inclusive)
        end_line: Ending line number (1-based, inclusive)
        respect_gitignore: Whether to respect .gitignore patterns (default: True)
        
    Returns:
        JSON with 'content' and optionally 'error' or 'info'
    """
    logger = get_logger()
    logger.debug(f"[TOOL] Entering read with path='{path}', start_line={start_line}, end_line={end_line}")
    
    # Validate path
    if not path:
        return json.dumps({"error": "No path provided."})
    
    # Check if file exists
    if not os.path.exists(path):
        return json.dumps({"error": f"File not found: {path}"})
    
    if not os.path.isfile(path):
        return json.dumps({"error": f"Path is not a file: {path}"})
    
    # Check gitignore if requested
    if respect_gitignore:
        # Get the directory containing the file for gitignore loading
        file_dir = os.path.dirname(os.path.abspath(path))
        spec = load_gitignore_patterns(file_dir or ".")
        
        if spec:
            # Check if file matches gitignore patterns
            rel_path = os.path.relpath(path, file_dir or ".")
            if spec.match_file(rel_path):
                logger.warning(f"[TOOL] File {path} is gitignored and respect_gitignore=True")
                return json.dumps({
                    "error": f"File '{path}' is ignored by .gitignore. Use respect_gitignore=False to read it anyway."
                })
    
    # Read file with optional line range
    try:
        with open(path, "r", encoding="utf-8") as f:
            if start_line is None and end_line is None:
                # Read entire file
                content = f.read()
                logger.debug(f"[TOOL] Read entire file, {len(content)} characters")
                return json.dumps({
                    "path": path,
                    "content": content
                })
            else:
                # Read specific line range
                lines = []
                start_idx = (start_line - 1) if start_line and start_line > 0 else 0
                end_idx = end_line if end_line and end_line > 0 else float("inf")
                
                for i, line in enumerate(f):
                    if i < start_idx:
                        continue
                    if i >= end_idx:
                        break
                    lines.append(line)
                
                if not lines:
                    return json.dumps({
                        "path": path,
                        "info": "No lines in specified range.",
                        "content": ""
                    })
                
                content = "".join(lines)
                result = {
                    "path": path,
                    "content": content
                }
                
                # Only include line numbers if they were specified
                if start_line is not None:
                    result["start_line"] = start_line
                if end_line is not None:
                    result["end_line"] = min(end_line, start_idx + len(lines))
                    
                logger.debug(f"[TOOL] Read {len(lines)} lines from file")
                return json.dumps(result)
                
    except UnicodeDecodeError:
        return json.dumps({
            "error": f"Cannot read file - it appears to be binary or uses unsupported encoding: {path}"
        })
    except Exception as e:
        logger.error(f"Error reading file {path}: {e}")
        return json.dumps({"error": f"Error reading file: {str(e)}"})