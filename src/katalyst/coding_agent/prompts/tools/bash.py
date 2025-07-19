from textwrap import dedent

BASH_TOOL_PROMPT = dedent("""
# bash Tool

Description: Execute shell commands in the terminal.

Parameters:
- command: (string, required) Shell command to execute
- cwd: (string, optional) Working directory for command execution
- timeout: (integer, optional) Timeout in seconds (default: 30)

Output: JSON with keys: 'success', 'command', 'cwd', 'stdout', 'stderr', 'error'

Examples:
- bash("ls -la")
- bash("npm install", cwd="/path/to/project")
- bash("python script.py", timeout=60)
""")