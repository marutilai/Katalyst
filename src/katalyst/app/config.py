# katalyst/app/config.py
# Central configuration and constants for the Katalyst Agent project.

from pathlib import Path

# Maximum number of search results to return from the search_files tool.
# This keeps output readable and prevents overwhelming the user or agent.
SEARCH_FILES_MAX_RESULTS = 20

# Map file extensions to language names for tree-sitter-languages
EXT_TO_LANG = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".jsx": "javascript",
}

# Directory for all Katalyst agent state, cache, and index files
KATALYST_DIR = Path(".katalyst")
KATALYST_DIR.mkdir(exist_ok=True)

# Onboarding flag (now inside .katalyst)
ONBOARDING_FLAG = KATALYST_DIR / "onboarded"

# Checkpoint database for conversation persistence
CHECKPOINT_DB = KATALYST_DIR / "checkpoints.db"

# Common directories and files to ignore in addition to .gitignore
KATALYST_IGNORE_PATTERNS = {
    # Version control
    ".git",
    ".svn",
    ".hg",
    # Build and cache
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.egg-info",
    # Environment
    ".env",
    "venv",
    ".venv",
    "env",
    # IDE
    ".idea",
    ".vscode",
    ".cursor",
    # OS
    ".DS_Store",
    "Thumbs.db",
    # Project specific
    ".katalyst",
}

#TODO: Explanatory Variable Names (Config Variables)
# Maximum number of tokens to return in the final output. Will be enforced only after summarization.
MAX_AGGREGATE_TOKENS_IN_SUMMARY_AND_OUTPUT = 50000 # 50k
# Maximum number of tokens to accumulate before triggering summarization.
MAX_TOKENS_TO_TRIGGER_SUMMARY = 40000 # 40k
# Maximum number of tokens to budget for the summary.
MAX_TOKENS_IN_SUMMARY_ONLY = 8000 # 8k