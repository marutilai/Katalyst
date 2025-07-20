from textwrap import dedent

BASH_TOOL_PROMPT = dedent("""
# bash Tool

Description: Execute shell commands in the terminal.

Parameters:
- command: (string, required) Shell command to execute
- cwd: (string, optional) Working directory for command execution
- timeout: (integer, optional) Timeout in seconds (default: 30)

Output: JSON with keys:
- success: Boolean indicating if command executed successfully
- command: The command that was executed
- cwd: Working directory used
- stdout: Standard output from command
- stderr: Standard error output (if any)
- error: Error message (if command failed)
- user_instruction: User feedback (if command was denied)

Examples:
- bash("ls -la")
- bash("npm install", cwd="/path/to/project")
- bash("python script.py", timeout=60)

Notes:
- Commands may require user approval
- Working directory defaults to project root
""")