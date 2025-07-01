from textwrap import dedent

LIST_FILES_TOOL_PROMPT = dedent("""
# list_files Tool

Description: List files and directories in a given path.

Parameters:
- path: (string, required) Directory path to list

Output: JSON with keys: 'path', 'entries' (list of file/directory names), 'error'
""")