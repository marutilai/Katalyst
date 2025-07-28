import os
import json
from pathlib import Path
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import katalyst_tool
from katalyst.katalyst_core.utils.file_utils import should_ignore_path


def _process_matches(matches, base_path, pattern, respect_gitignore):
    """
    Helper function to process glob matches and filter them.
    
    Returns:
        List of relative file paths that pass all filters
    """
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
    
    return files


@katalyst_tool(prompt_module="glob", prompt_var="GLOB_TOOL_PROMPT", categories=["planner", "executor"])
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
        files = _process_matches(matches, base_path, pattern, respect_gitignore)
        
        # Sort for consistent output
        files.sort()
        
        # If no files found and pattern doesn't contain wildcards, try expanded patterns
        attempted_patterns = [pattern]
        if not files and '*' not in pattern and '?' not in pattern:
            # Try with wildcards
            expanded_patterns = [
                f"*{pattern}*",           # Partial match anywhere
                f"**/*{pattern}*",        # Recursive partial match
                f"{pattern}*",            # Prefix match
                f"*{pattern}",            # Suffix match
            ]
            
            for expanded_pattern in expanded_patterns:
                logger.debug(f"[TOOL] No exact match, trying expanded pattern: {expanded_pattern}")
                attempted_patterns.append(expanded_pattern)
                
                # Try the expanded pattern
                if expanded_pattern.startswith("**/"):
                    pattern_to_use = expanded_pattern[3:]
                    matches = list(base_path.rglob(pattern_to_use))
                else:
                    matches = list(base_path.glob(expanded_pattern))
                
                # Process matches using helper function
                new_files = _process_matches(matches, base_path, expanded_pattern, respect_gitignore)
                files.extend(new_files)
                
                # If we found files with this pattern, stop trying others
                if files:
                    files = list(set(files))  # Remove duplicates
                    files.sort()
                    break
            
            # If still no files and pattern has alphabetic chars, try case-insensitive
            if not files and any(c.isalpha() for c in pattern):
                logger.debug(f"[TOOL] No matches found, trying case-insensitive search")
                pattern_lower = pattern.lower()
                
                # Get all files and filter by case-insensitive match
                all_matches = []
                if "**" in pattern or "/" in pattern:
                    # For complex patterns, skip case-insensitive
                    pass
                else:
                    # Simple filename pattern - do case-insensitive search
                    all_files = list(base_path.rglob("*"))
                    case_insensitive_matches = [
                        f for f in all_files 
                        if f.is_file() and pattern_lower in f.name.lower()
                    ]
                    
                    # Process matches using helper function
                    files = _process_matches(case_insensitive_matches, base_path, pattern, respect_gitignore)
                    
                    if files:
                        files.sort()
                        attempted_patterns.append(f"{pattern} (case-insensitive)")
        
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
            result["info"] = f"No files found. Tried patterns: {', '.join(attempted_patterns)}"
        elif len(attempted_patterns) > 1:
            result["info"] = f"Found matches using expanded pattern: {attempted_patterns[-1]}"
        
        logger.debug(f"[TOOL] Exiting glob successfully, found {len(files)} files")
        return json.dumps(result)
        
    except Exception as e:
        logger.error(f"Error in glob pattern matching: {e}")
        return json.dumps({"error": f"Error processing glob pattern: {str(e)}"})