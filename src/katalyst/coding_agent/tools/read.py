import os
import json
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import katalyst_tool


@katalyst_tool(prompt_module="read", prompt_var="READ_TOOL_PROMPT")
def read(
    path: str,
    start_line: int = None,
    end_line: int = None,
    auto_approve: bool = True
) -> str:
    """
    Read the contents of a file, optionally from a specific line range.
    
    Args:
        path: File path to read
        start_line: Starting line number (1-based, inclusive)
        end_line: Ending line number (1-based, inclusive)
        
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