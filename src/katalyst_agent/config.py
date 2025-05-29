# src/katalyst_agent/config.py
# Central configuration and constants for the Katalyst Agent project.

from pathlib import Path

# Maximum number of search results to return from the search_files tool.
# This keeps output readable and prevents overwhelming the user or agent.
SEARCH_FILES_MAX_RESULTS = 20

# Map file extensions to language names for tree-sitter-languages
EXT_TO_LANG = {
    '.py': 'python',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'tsx',
    '.jsx': 'javascript',
}

# Onboarding and project state persistence
ONBOARDING_FLAG = Path.home() / ".katalyst_agent_onboarded"
STATE_FILE = ".katalyst_state.json" 