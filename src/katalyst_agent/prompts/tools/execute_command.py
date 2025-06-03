# Prompt for execute_command tool

from textwrap import dedent

EXECUTE_COMMAND_PROMPT = dedent("""
# execute_command Tool

Description: Use this tool to request execution of a CLI command on the user's system. Provide a clear, safe command and explain what it does. Prefer relative paths and non-interactive commands. Use the `cwd` parameter to specify a working directory if needed. For long-running commands, use the `timeout` parameter.

## Parameters for 'action_input' object:
- command: (string, required) The CLI command to execute.
- cwd: (string, optional) Working directory for the command (default: current directory).
- timeout: (integer, optional, in seconds) For commands that run indefinitely (e.g., dev servers).

## Example of how to structure your JSON response to use this tool:
{
  "thought": "The user requested to list files in the current directory. I will use execute_command to run 'ls -la'.",
  "action": "execute_command",
  "action_input": {
    "command": "ls -la",
    "cwd": "."
  }
}

Another example, with a timeout:
{
  "thought": "The user wants to start the dev server. I will use execute_command to run 'npm run dev' with a timeout.",
  "action": "execute_command",
  "action_input": {
    "command": "npm run dev",
    "timeout": 10
  }
}

## Tool Output Format (Observation):
The tool will return a JSON string as its observation. This JSON object will have the following keys:
- 'success': (boolean) True if the command executed successfully, False otherwise.
- 'command': (string) The command that was run.
- 'cwd': (string) The working directory where the command was run.
- 'stdout': (string, optional) The standard output from the command, if any.
- 'stderr': (string, optional) The standard error output from the command, if any.
- 'error': (string, optional) An error message if something went wrong (e.g., command failed, timed out, not found).
- 'user_instruction': (string, optional) If the user denied execution, their feedback or instruction will be here.

## Example Tool Outputs (Observation JSON):

Example 1: Successful command execution:
{
  "success": true,
  "command": "ls -la",
  "cwd": ".",
  "stdout": "total 8\ndrwxr-xr-x  3 user  staff   96 Jun  1 10:00 .\ndrwxr-xr-x  5 user  staff  160 Jun  1 09:59 ..\n-rw-r--r--  1 user  staff    0 Jun  1 10:00 file.txt"
}

Example 2: Command failed:
{
  "success": false,
  "command": "ls non_existent_dir",
  "cwd": ".",
  "stderr": "ls: non_existent_dir: No such file or directory",
  "error": "Command 'ls non_existent_dir' failed with code 1."
}

Example 3: User denied execution:
{
  "success": false,
  "command": "rm -rf /",
  "cwd": ".",
  "user_instruction": "Do not run destructive commands."
}

Example 4: Command timed out:
{
  "success": false,
  "command": "sleep 1000",
  "cwd": ".",
  "error": "Command 'sleep 1000' timed out after 10 seconds."
}

Example 5: Command not found:
{
  "success": false,
  "command": "foobarbaz",
  "cwd": ".",
  "error": "Command not found: foobarbaz. Please ensure it's installed and in PATH."
}
""")
