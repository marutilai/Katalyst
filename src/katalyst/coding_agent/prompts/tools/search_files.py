from textwrap import dedent

SEARCH_FILES_PROMPT = dedent("""
# regex_search_inside_files Tool

Description: Search for regex patterns inside files.

Parameters:
- path: (string, required) Directory to search in
- regex: (string, required) Regex pattern to search
- file_pattern: (string, optional) File pattern filter (e.g., "*.py")

Output: JSON with keys: 'matches' (list of file paths with matches), 'error'
""")