from textwrap import dedent

READ_FILE_TOOL_PROMPT = dedent("""
# read_file Tool

Description: Read the contents of a specific file.

Parameters:
- path: (string, required) File path to read
- start_line: (integer, optional) Starting line number (1-based)
- end_line: (integer, optional) Ending line number (1-based)

Output: JSON with keys: 'path', 'start_line', 'end_line', 'content', 'content_ref', 'info', 'error'
""")