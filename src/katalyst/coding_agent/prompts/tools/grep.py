from textwrap import dedent

GREP_TOOL_PROMPT = dedent("""
# grep Tool

Description: Search for patterns in files using regular expressions.

Parameters:
- pattern: (string, required) Regular expression pattern to search for
- path: (string, optional) Directory or file to search in (default: current directory)
- file_pattern: (string, optional) Glob pattern to filter files (e.g., "*.py", "*.js")
- case_insensitive: (boolean, optional) Perform case-insensitive search (default: False)
- show_line_numbers: (boolean, optional) Include line numbers in results (default: True)
- max_results: (integer, optional) Maximum number of results to return

Output: JSON with keys: 'matches' (list of match objects with 'file', 'line', 'content'), 'info', 'error'

Examples:
- grep("TODO")  # Search for TODO in current directory
- grep("class.*Model", path="src/", file_pattern="*.py")  # Search Python files for class definitions
- grep("error", case_insensitive=True)  # Case-insensitive search for "error"
- grep("import React", file_pattern="*.jsx")  # Search JSX files for React imports

Notes:
- Uses ripgrep (rg) for fast searching
- Automatically excludes: node_modules/, __pycache__/, .git/, .env, *.pyc, venv/
- Shows 2 lines of context around matches
- Supports full regex syntax
""")