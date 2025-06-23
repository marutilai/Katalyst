from textwrap import dedent

EXECUTE_COMMAND_PROMPT = dedent("""
# execute_command Tool

Description: Execute CLI commands on the user's system. Provide clear, safe commands. Use relative paths and non-interactive commands.

## When to Use:
- Running build commands (npm install, pip install, make)
- Executing tests (pytest, npm test)
- Running linters or formatters
- Git operations (status, log, diff)
- System information queries (pwd, env, which)
- File operations when other tools aren't suitable

## Parameters:
- command: (string, required) CLI command to execute
- cwd: (string, optional) Working directory (default: current)
- timeout: (integer, optional) Timeout in seconds for long-running commands

## Example:
{
  "thought": "I need to install project dependencies.",
  "action": "execute_command",
  "action_input": {
    "command": "npm install",
    "cwd": "."
  }
}

## Output Format:
JSON with keys: 'success' (boolean), 'command', 'cwd', 'stdout' (optional), 'stderr' (optional), 'error' (optional), 'user_instruction' (optional)

Example outputs:
- Success: {"success": true, "command": "ls -la", "cwd": ".", "stdout": "total 8\\ndrwxr-xr-x..."}
- Failed: {"success": false, "command": "ls missing", "error": "Command failed with code 1"}
- Denied: {"success": false, "command": "rm -rf /", "user_instruction": "Do not run destructive commands"}
- Timeout: {"success": false, "command": "sleep 1000", "error": "Command timed out after 10 seconds"}
""")
