import os
import json
from pathlib import Path
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import katalyst_tool
from katalyst.katalyst_core.utils.file_utils import should_ignore_path


@katalyst_tool(prompt_module="glob", prompt_var="GLOB_TOOL_PROMPT")
def glob(
    pattern: str,
    path: str = ".",
    respect_gitignore: bool = True,
    auto_approve: bool = True
) -> str:
    """
    Find files matching a glob pattern.
    
    Args:
        pattern: Glob pattern to match (e.g., "*.py", "**/*.test.js")
        path: Base directory to search from (default: current directory)
        respect_gitignore: Whether to filter out gitignored files (default: True)
        
    Returns:
        JSON with 'pattern', 'base_path', and 'files' (list of matching paths)
    """
    logger = get_logger()
    logger.debug(f"[TOOL] Entering glob with pattern='{pattern}', path='{path}', respect_gitignore={respect_gitignore}")
    
    # Validate inputs
    if not pattern:
        return json.dumps({"error": "No pattern provided."})
    
    # Use current directory if not specified
    if not path:
        path = "."
    
    # Check if base path exists
    if not os.path.exists(path):
        return json.dumps({"error": f"Base path not found: {path}"})
    
    # Convert to Path object for easier manipulation
    base_path = Path(path).resolve()
    
    try:
        # Use Path.glob for pattern matching
        if pattern.startswith("**/"):
            # For recursive patterns, use rglob
            pattern_to_use = pattern[3:]  # Remove leading **/
            matches = list(base_path.rglob(pattern_to_use))
        elif "**" in pattern:
            # Handle patterns with ** in the middle
            matches = list(base_path.glob(pattern))
        else:
            # Non-recursive patterns
            matches = list(base_path.glob(pattern))
        
        # Convert to relative paths and filter
        files = []
        for match in matches:
            # Skip directories unless explicitly looking for them
            if match.is_dir() and not pattern.endswith("/"):
                continue
            
            # Get relative path
            try:
                rel_path = match.relative_to(base_path)
            except ValueError:
                # If can't get relative path, use absolute
                rel_path = match
            
            # Check gitignore if requested
            if respect_gitignore:
                if should_ignore_path(str(rel_path), str(base_path), respect_gitignore):
                    continue
            
            files.append(str(rel_path))
        
        # Sort for consistent output
        files.sort()
        
        # Limit results to prevent overwhelming output
        max_results = 100
        truncated = False
        if len(files) > max_results:
            files = files[:max_results]
            truncated = True
        
        result = {
            "pattern": pattern,
            "base_path": str(base_path),
            "files": files
        }
        
        if truncated:
            result["info"] = f"Results truncated to {max_results} files."
        elif not files:
            result["info"] = f"No files found matching pattern '{pattern}'."
        
        logger.debug(f"[TOOL] Exiting glob successfully, found {len(files)} files")
        return json.dumps(result)
        
    except Exception as e:
        logger.error(f"Error in glob pattern matching: {e}")
        return json.dumps({"error": f"Error processing glob pattern: {str(e)}"})