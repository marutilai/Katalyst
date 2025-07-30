import os
from typing import Set, Optional
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


def resolve_and_validate_path(path: str, project_root: str) -> str:
    """
    Resolve a path and validate it's within the project sandbox.
    
    Args:
        path: The path to validate (can be relative, absolute, or contain ~)
        project_root: The project root directory (sandbox boundary)
        
    Returns:
        str: The resolved absolute path
        
    Raises:
        SandboxViolationError: If the path is outside the project directory
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
            raise SandboxViolationError(path, project_root)
    except ValueError:
        # Paths are on different drives (Windows) or have no common path
        raise SandboxViolationError(path, project_root)
    
    return resolved_path
