import os
import re
from typing import Set, Optional, List, Union
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern
from katalyst.app.config import KATALYST_IGNORE_PATTERNS
from katalyst.katalyst_core.utils.exceptions import SandboxViolationError


def load_gitignore_patterns(root_path: str) -> Optional[PathSpec]:
    """Load .gitignore patterns from the given directory."""
    gitignore_path = os.path.join(root_path, ".gitignore")
    if not os.path.exists(gitignore_path):
        return None

    try:
        with open(gitignore_path, "r") as f:
            patterns = f.read().splitlines()
        return PathSpec.from_lines(GitWildMatchPattern, patterns)
    except Exception:
        return None


def should_ignore_path(
    path: str,
    root_path: str,
    respect_gitignore: bool = True,
    additional_patterns: Optional[Set[str]] = None,
) -> bool:
    """
    Check if a path should be ignored based on Katalyst patterns and .gitignore.

    Args:
        path: The path to check (relative to root_path)
        root_path: The root directory path
        respect_gitignore: Whether to respect .gitignore patterns
        additional_patterns: Additional patterns to ignore

    Returns:
        bool: True if the path should be ignored
    """
    # Check Katalyst ignore patterns
    parts = path.split(os.sep)
    if any(pattern in parts for pattern in KATALYST_IGNORE_PATTERNS):
        return True

    # Check additional patterns if provided
    if additional_patterns and any(pattern in parts for pattern in additional_patterns):
        return True

    # Check .gitignore if enabled
    if respect_gitignore:
        spec = load_gitignore_patterns(root_path)
        if spec and spec.match_file(path):
            return True

    return False


def _is_path_in_allowed_list(
    path: str, 
    resolved_path: str, 
    allowed_external_paths: Optional[Union[List[str], Set[str]]]
) -> bool:
    """
    Check if a path is in the allowed external paths list.
    
    This helper function ensures consistent validation logic across different
    code paths, preventing security vulnerabilities from inconsistent checks.
    
    Args:
        path: Original path provided by user
        resolved_path: The resolved absolute path
        allowed_external_paths: List or Set of allowed external paths
        
    Returns:
        bool: True if the path is allowed, False otherwise
    """
    if not allowed_external_paths:
        return False
    
    for allowed in allowed_external_paths:
        # Resolve the allowed path for comparison
        allowed_expanded = os.path.expanduser(allowed) if allowed.startswith("~") else allowed
        allowed_abs = os.path.abspath(allowed_expanded) if not os.path.isabs(allowed_expanded) else allowed_expanded
        try:
            allowed_resolved = os.path.realpath(allowed_abs)
            # Check both resolved paths and original path strings
            if resolved_path == allowed_resolved or path == allowed:
                return True
        except OSError:
            # If we can't resolve allowed path, do string comparison only
            if path == allowed:
                return True
    
    return False


def resolve_and_validate_path(path: str, project_root: str, allowed_external_paths: Optional[Union[List[str], Set[str]]] = None) -> str:
    """
    Resolve a path and validate it's within the project sandbox.
    
    Args:
        path: The path to validate (can be relative, absolute, or contain ~)
        project_root: The project root directory (sandbox boundary)
        allowed_external_paths: List or Set of external paths explicitly allowed by user
        
    Returns:
        str: The resolved absolute path
        
    Raises:
        SandboxViolationError: If the path is outside the project directory and not in allowed list
    """
    # Handle empty or None path
    if not path:
        path = "."
    
    # Expand user home directory
    if path.startswith("~"):
        path = os.path.expanduser(path)
    
    # If path is relative, make it absolute relative to project root
    if not os.path.isabs(path):
        path = os.path.join(project_root, path)
    
    # Resolve the path (follows symlinks, removes .., etc)
    try:
        resolved_path = os.path.realpath(path)
        project_root_resolved = os.path.realpath(project_root)
    except Exception as e:
        # If we can't resolve, it's likely an invalid path
        raise SandboxViolationError(path, project_root) from e
    
    # Check if the resolved path is within the project root
    # Use os.path.commonpath to check if paths share a common prefix
    try:
        common_path = os.path.commonpath([resolved_path, project_root_resolved])
        if common_path != project_root_resolved:
            # Path is outside project - check if it's in allowed list
            if _is_path_in_allowed_list(path, resolved_path, allowed_external_paths):
                return resolved_path
            raise SandboxViolationError(path, project_root)
    except ValueError:
        # Paths are on different drives (Windows) or have no common path
        # Check allowed list before raising error
        if _is_path_in_allowed_list(path, resolved_path, allowed_external_paths):
            return resolved_path
        raise SandboxViolationError(path, project_root)
    
    return resolved_path


def extract_file_paths(text: str) -> List[str]:
    """
    Extract file paths from user text.
    
    Looks for:
    - Absolute paths: /path/to/file
    - Home paths: ~/path/to/file
    - Relative paths with ..: ../path/to/file
    - Windows paths: C:\\path\\to\\file
    
    Args:
        text: User input text
        
    Returns:
        List of detected file paths
    """
    paths = []
    
    # Patterns to match different types of paths
    patterns = [
        # Home directory paths (~/...)
        r'(~(?:/[a-zA-Z0-9_\-./]+)+)',
        # Relative paths with .. (../...)
        r'(\.\.(?:/[a-zA-Z0-9_\-./]+)+)',
        # Unix/Linux/Mac absolute paths (start with / and contain at least one more /)
        r'(?:^|\s)(/(?:[a-zA-Z0-9_\-]+/)+[a-zA-Z0-9_\-./]*)',
        # Windows paths with backslashes
        r'([a-zA-Z]:\\\\[a-zA-Z0-9_\-.\\\\ ]+)',
        # Windows paths with forward slashes
        r'([a-zA-Z]:/[a-zA-Z0-9_\-./]+)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        paths.extend(matches)
    
    # Deduplicate while preserving order
    return list(dict.fromkeys(paths))


def extract_and_classify_paths(text: str, project_root: str) -> List[str]:
    """
    Extract file paths from text and return only those outside the project.
    
    Args:
        text: User input text
        project_root: The project root directory
        
    Returns:
        List of external file paths that should be added to allowed list
    """
    paths = extract_file_paths(text)
    external_paths = []
    
    for path in paths:
        # Expand ~ to home directory
        if path.startswith("~"):
            path = os.path.expanduser(path)
        
        # Convert to absolute path if relative to project
        if not os.path.isabs(path):
            path = os.path.join(project_root, path)
        
        # Check if it's outside project root
        try:
            resolved = os.path.realpath(path)
            project_resolved = os.path.realpath(project_root)
            common = os.path.commonpath([resolved, project_resolved])
            if common != project_resolved:
                # This path is outside the project
                external_paths.append(path)
        except (OSError, ValueError):
            # If we can't resolve, assume it's external to be safe
            external_paths.append(path)
    
    return external_paths
