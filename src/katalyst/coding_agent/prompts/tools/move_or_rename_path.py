from textwrap import dedent

MOVE_OR_RENAME_PATH_TOOL_PROMPT = dedent("""
# move_or_rename_path Tool

Description: Move or rename files and directories.

Parameters:
- source_path: (string, required) Current path
- destination_path: (string, required) New path

Output: JSON with keys: 'success', 'source_path', 'destination_path', 'error'
""")