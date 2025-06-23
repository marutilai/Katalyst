from textwrap import dedent

LIST_FILES_PROMPT = dedent("""
# list_files Tool

Description: List files and directories in a given directory. Directories shown with '/' suffix.

## When to Use:
- Exploring project structure
- Finding specific files or directories
- Checking if files exist before operations
- Understanding directory contents
- Discovering configuration files

## Parameters:
- path: (string, required) Directory path to list
- recursive: (boolean, required) true for recursive listing, false for top-level only

## Example:
{
  "thought": "I need to see what files are in the src directory.",
  "action": "list_files",
  "action_input": {
    "path": "src",
    "recursive": false
  }
}

## Output Format:
JSON with keys: 'path', 'files' (list of strings, optional), 'error' (optional)

Note: Directories have '/' suffix

Example outputs:
- Success: {"path": ".", "files": ["src/", "pyproject.toml", "README.md"]}
- Not found: {"path": "missing/", "error": "Path does not exist"}
- Empty: {"path": "empty_dir/", "files": []}
""")