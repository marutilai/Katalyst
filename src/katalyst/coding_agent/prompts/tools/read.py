from textwrap import dedent

READ_TOOL_PROMPT = dedent("""
# read Tool

Description: Read the contents of a file, with optional line range support.

Parameters:
- path: (string, required) File path to read
- start_line: (integer, optional) Starting line number (1-based, inclusive)
- end_line: (integer, optional) Ending line number (1-based, inclusive)

Output: JSON with keys:
- path: The file path that was read
- content: The file content
- start_line: Starting line (only if specified)
- end_line: Ending line (only if specified)
- info: Informational message (if applicable)
- error: Error message (if read failed)

Examples:
- read("config.py")  # Read entire file
- read("large_file.py", start_line=100, end_line=150)  # Read lines 100-150
- read("src/main.py", start_line=1, end_line=50)  # Read first 50 lines
- read("README.md", start_line=10)  # Read from line 10 to end

Notes:
- Line numbers are 1-based (first line is 1, not 0)
- Both start_line and end_line are inclusive
- If only start_line is provided, reads from that line to end of file
- If only end_line is provided, reads from beginning to that line
- Returns empty content with info message if no lines in range
""")