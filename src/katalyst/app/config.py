# katalyst/app/config.py
# Central configuration and constants for the Katalyst Agent project.

import os
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

# Conversation summarization thresholds
# Maximum tokens allowed in conversation after summarization
MAX_AGGREGATE_TOKENS = 50000  # 50k

# Token count that triggers summarization
MAX_TOKENS_BEFORE_SUMMARY = 40000  # 40k

# Maximum tokens allocated for the summary itself
MAX_SUMMARY_TOKENS = 8000  # 8k

# --- Agent Behavior Configuration ---
# Whether to auto-approve file modifications without prompting
AUTO_APPROVE = os.getenv("KATALYST_AUTO_APPROVE", "true").lower() == "true"

# Maximum cycles for outer planning loop
MAX_OUTER_CYCLES = int(os.getenv("KATALYST_MAX_OUTER_CYCLES", "5"))

# Maximum cycles for inner execution loop
MAX_INNER_CYCLES = int(os.getenv("KATALYST_MAX_INNER_CYCLES", "20"))

# LangGraph recursion limit
RECURSION_LIMIT = int(os.getenv("KATALYST_RECURSION_LIMIT", "250"))

# Whether to use playbooks with task type classification
USE_PLAYBOOKS = os.getenv("KATALYST_USE_PLAYBOOKS", "true").lower() == "true"
