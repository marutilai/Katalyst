from textwrap import dedent

EXECUTE_COMMAND_TOOL_PROMPT = dedent("""
# execute_command Tool

Description: Execute shell commands in the project directory.

Parameters:
- command: (string, required) Shell command to execute

Output: JSON with keys: 'stdout', 'stderr', 'return_code', 'error'
""")