from textwrap import dedent

WRITE_TOOL_PROMPT = dedent("""
# write Tool

Description: Write content to a file, creating directories as needed.

Parameters:
- path: (string, required) File path to write
- content: (string, required) Content to write
- auto_approve: (boolean, optional) Skip user confirmation (default: True)

Output: JSON with keys:
- success: Whether the write operation succeeded
- path: The file path that was written
- created: True if file was newly created, False if it was updated
- cancelled: True if user declined or operation was cancelled
- info: Informational message about the operation
- error: Error message if write failed

Examples:
- write("config.py", "DEBUG = True\\nPORT = 8080")
- write("src/main.py", updated_code)
- write("data.json", json_string, auto_approve=False)

Notes:
- Creates parent directories automatically
- Validates syntax for code files
""")