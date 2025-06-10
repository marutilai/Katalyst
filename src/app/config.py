# src/app/config.py
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

# State file for the agent (now inside .katalyst)
KATALYST_STATE_FILE = KATALYST_DIR / "katalyst_state.json"
