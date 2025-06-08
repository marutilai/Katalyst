import os
import pathspec

def load_gitignore_patterns(path: str):
    """
    Loads .gitignore patterns from the given path using pathspec.
    Returns a PathSpec object or None if not available.
    """
    patterns = []
    gitignore_path = os.path.join(path, '.gitignore')
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            patterns = f.read().splitlines()
    if patterns:
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
    return None 