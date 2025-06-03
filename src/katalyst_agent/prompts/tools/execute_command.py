# Prompt for execute_command tool

from textwrap import dedent

EXECUTE_COMMAND_PROMPT = dedent("""
# execute_command Tool

Use this tool to request execution of a CLI command on the user's system. Provide a clear, safe command and explain what it does. Prefer relative paths and non-interactive commands. Use the `cwd` parameter to specify a working directory if needed. For long-running commands, use the `timeout` parameter.

## Parameters:
- command: (required) The CLI command to execute.
- cwd: (optional) Working directory for the command (default: current directory).
- timeout: (optional, in seconds) For commands that run indefinitely (e.g., dev servers).

## Note:
- Do not use 'cd' to change directories; use the `cwd` parameter instead.
- The command will run in a non-interactive shell. If user interaction is required, ask the user via ask_followup_question.

## Usage
<execute_command>
<command>Your command here</command>
<cwd>Optional working directory</cwd>
<timeout>Optional timeout</timeout>
</execute_command>

## Example
<execute_command>
<command>npm run dev</command>
<timeout>10</timeout>
</execute_command>

<execute_command>
<command>ls -la</command>
<cwd>/home/user/projects</cwd>
</execute_command>
""")
