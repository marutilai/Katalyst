from textwrap import dedent

WRITE_TO_FILE_TOOL_PROMPT = dedent("""
# write_to_file Tool

Description: Create a new file or completely overwrite an existing file.

Parameters:
- path: (string, required) File path to write
- content: (string, required) Content to write
- content_ref: (string, optional) Reference to preserve exact content

Output: JSON with keys: 'path', 'info', 'error'
""")