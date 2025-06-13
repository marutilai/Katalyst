import os
from typing import List, Set, Optional
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


def filter_paths(
    paths: List[str],
    root_path: str,
    respect_gitignore: bool = True,
    additional_patterns: Optional[Set[str]] = None,
) -> List[str]:
    """
    Filter a list of paths based on Katalyst patterns and .gitignore.

    Args:
        paths: List of paths to filter
        root_path: The root directory path
        respect_gitignore: Whether to respect .gitignore patterns
        additional_patterns: Additional patterns to ignore

    Returns:
        List[str]: Filtered list of paths
    """
    return [
        path
        for path in paths
        if not should_ignore_path(
            path, root_path, respect_gitignore, additional_patterns
        )
    ]


def list_files_recursively(
    root_path: str,
    respect_gitignore: bool = True,
    additional_patterns: Optional[Set[str]] = None,
) -> List[str]:
    """
    Recursively list all files under root_path, respecting .gitignore and KATALYST_IGNORE_PATTERNS.
    Returns a list of file paths (relative to root_path).
    """
    file_list = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Compute relative path for filtering
        rel_dir = os.path.relpath(dirpath, root_path)
        # Filter out ignored directories in-place
        dirnames[:] = [
            d
            for d in dirnames
            if not should_ignore_path(
                os.path.join(rel_dir, d) if rel_dir != "." else d,
                root_path,
                respect_gitignore,
                additional_patterns,
            )
        ]
        for fname in filenames:
            rel_file = (
                os.path.normpath(os.path.join(rel_dir, fname))
                if rel_dir != "."
                else fname
            )
            if not should_ignore_path(
                rel_file, root_path, respect_gitignore, additional_patterns
            ):
                file_list.append(os.path.join(dirpath, fname))
    return file_list
