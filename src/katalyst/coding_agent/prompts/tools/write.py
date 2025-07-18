from textwrap import dedent

WRITE_TOOL_PROMPT = dedent("""
# write Tool

Description: Write content to a file, creating directories as needed. Validates syntax for supported file types.

Parameters:
- path: (string, required) File path to write to
- content: (string, required) Content to write to the file
- auto_approve: (boolean, optional) Skip user confirmation (default: True)

Output: JSON with keys:
- success: Whether the write operation succeeded
- path: The file path that was written
- created: True if file was newly created, False if it was updated
- cancelled: True if user declined or operation was cancelled
- info: Informational message about the operation
- error: Error message if write failed

Features:
- Automatic syntax validation for Python, JavaScript, and other supported file types
- Creates parent directories automatically if they don't exist
- Shows preview of content before writing
- Supports user approval workflow when auto_approve=False
- UTF-8 encoding for all files

Examples:
- write("config.py", "DEBUG = True\\nPORT = 8080")  # Create new config file
- write("src/main.py", updated_code)  # Update existing file
- write("docs/README.md", markdown_content)  # Create file in new directory
- write("data.json", json_string, auto_approve=False)  # Ask for confirmation

Notes:
- Syntax errors will prevent writing (for supported file types)
- Parent directories are created automatically
- Files are always written with UTF-8 encoding
- Shows a preview of first/last 5 lines for large files
""")