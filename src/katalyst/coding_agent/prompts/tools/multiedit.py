from textwrap import dedent

MULTIEDIT_TOOL_PROMPT = dedent("""
# multiedit Tool

Description: Apply multiple string replacements to a file in one operation.

Parameters:
- file_path: (string, required) Path to file
- edits: (array, required) List of edit objects with:
  - old_string: (string) Exact string to replace
  - new_string: (string) Replacement string

Output: JSON with 'success', 'file_path', 'info' or 'error'

Example:
- multiedit("app.py", [
    {"old_string": "port = 3000", "new_string": "port = 8080"},
    {"old_string": "debug = False", "new_string": "debug = True"}
  ])

Notes:
- All edits validated before applying
- Replaces all occurrences of each string
- Checks syntax for code files
""")