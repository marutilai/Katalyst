from textwrap import dedent

EDIT_TOOL_PROMPT = dedent("""
# edit Tool

Description: Replace exact string in a file. Fails if string appears multiple times.

Parameters:
- file_path: (string, required) Path to file  
- old_string: (string, required) Exact string to replace
- new_string: (string, required) Replacement string

Output: JSON with 'success', 'file_path', 'info' or 'error'

Examples:
- edit("config.py", "DEBUG = False", "DEBUG = True")
- edit("app.js", "const port = 3000", "const port = 8080")

Notes:
- Requires exact match including whitespace
- Use MultiEdit for multiple replacements
- Checks syntax for code files
""")