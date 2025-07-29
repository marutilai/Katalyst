import os
from typing import Set, Optional
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern
from katalyst.app.config import KATALYST_IGNORE_PATTERNS


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




