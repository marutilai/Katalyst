from textwrap import dedent

WRITE_TO_FILE_PROMPT = dedent("""
# write_to_file Tool

Description: Write full content to a file. Overwrites existing files or creates new ones (including directories). Provide complete content—no truncation.

## When to Use:
- Creating new files or replacing file contents entirely
- Setting up project structure (creates parent directories automatically)
- Writing configuration files, scripts, or documentation
- Saving generated output or results
- Creating empty marker files like __init__.py

## Parameters:
- path: (string, required) File path to write
- content: (string, required) Full content to write
- auto_approve: (boolean, optional) Skip user confirmation if true

## Example:
{
  "thought": "I want to create a new config file.",
  "action": "write_to_file",
  "action_input": {
    "path": "config.json",
    "content": "{\\n  \"apiEndpoint\": \"https://api.example.com\"\\n}"
  }
}

## Output Format:
JSON with keys: 'success' (boolean), 'path', 'info' (optional), 'error' (optional), 'cancelled' (optional)

Example outputs:
- Success: {"success": true, "path": "/path/to/file.json", "info": "Successfully wrote to file"}
- Declined: {"success": false, "path": "/path/to/file.json", "cancelled": true, "info": "User declined"}
- Error: {"success": false, "path": "/path/to/file.py", "error": "Syntax error in content"}
""")