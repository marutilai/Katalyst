from textwrap import dedent

GREP_TOOL_PROMPT = dedent("""
# grep Tool

Description: Search for patterns in files using regular expressions.

Parameters:
- pattern: (string, required) Regular expression pattern to search
- path: (string, optional) Directory or file to search (default: current)
- file_pattern: (string, optional) Glob pattern to filter files (e.g., "*.py")
- case_insensitive: (boolean, optional) Case-insensitive search (default: False)
- show_line_numbers: (boolean, optional) Include line numbers (default: True)
- max_results: (integer, optional) Limit results

Output: JSON with 'matches' list (file, line, content), 'info', 'error'

Examples:
- grep("TODO")                                    # Search for TODO
- grep("class.*Model", path="src/", file_pattern="*.py")  # Find class definitions
- grep("error", case_insensitive=True)           # Case-insensitive search

Notes:
- Uses ripgrep for fast searching
- Auto-excludes common directories (node_modules, .git, etc.)
""")