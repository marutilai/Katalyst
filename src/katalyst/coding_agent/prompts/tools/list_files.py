# coding_agent/prompts/tools/list_files.py
from textwrap import dedent

LIST_FILES_PROMPT = dedent("""
# list_files Tool

Description: List files and directories in a given directory. Set `recursive` to true for recursive listing, false for top-level only.

## Parameters:
- path: (string, required) Directory path to list
- recursive: (boolean, required) true for recursive, false for top-level only

## Example:
"action_input": {
  "path": "src",
  "recursive": false
}

## Output Format:
JSON with keys: 'path', 'files' (list of strings, optional), 'error' (optional)

Directories have '/' suffix. Example outputs:
- Success: {"path": ".", "files": ["src/", "pyproject.toml"]}
- Not found: {"path": "missing/", "error": "Path does not exist"}
- Empty: {"path": "empty_dir/", "files": []}
""")
