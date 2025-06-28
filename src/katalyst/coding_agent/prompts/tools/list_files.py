from textwrap import dedent

LIST_FILES_PROMPT = dedent("""
# list_files Tool

Description: List files and directories in a given directory. Directories shown with '/' suffix.

## When to Use:
- Exploring project structure
- Finding specific files or directories by name
- Checking if files exist before operations
- Understanding directory contents
- Discovering configuration files

## Parameters:
- path: (string, required) Directory path to list (use absolute path from project root, e.g., 'project_folder/subfolder' not just 'subfolder')
- recursive: (boolean, required) true for recursive listing, false for top-level only
  - Use recursive: false for initial exploration or when you know the file is in a specific directory
  - Use recursive: true when searching for files across nested directories

## Example:
{
  "thought": "I need to see what files are in this directory.",
  "action": "list_files",
  "action_input": {
    "path": "project_folder/subfolder",
    "recursive": false
  }
}

## Output Format:
JSON with keys: 'path', 'files' (list of strings, optional), 'error' (optional)

Note: Directories have '/' suffix

Example outputs:
- Success: {"path": ".", "files": ["folder1/", "folder2/", "file1.py", "file2.txt"]}
- Not found: {"path": "missing/", "error": "Path does not exist"}
- Empty: {"path": "empty_dir/", "files": []}
""")