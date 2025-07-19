from textwrap import dedent

READ_TOOL_PROMPT = dedent("""
# read Tool

Description: Read file contents with optional line range.

Parameters:
- path: (string, required) File path to read
- start_line: (integer, optional) Starting line (1-based, inclusive)
- end_line: (integer, optional) Ending line (1-based, inclusive)
- respect_gitignore: (boolean, optional) Filter gitignored files (default: True)

Output: JSON with keys:
- path: The file path that was read
- content: The file content
- start_line: Starting line (only if specified)
- end_line: Ending line (only if specified)
- info: Informational message (if applicable)
- error: Error message (if read failed)

Examples:
- read("config.py")                           # Read entire file
- read("main.py", start_line=100, end_line=150)  # Read lines 100-150
- read(".env", respect_gitignore=False)       # Read gitignored file

Notes:
- Line numbers are 1-based
- Partial ranges supported (start or end only)
""")