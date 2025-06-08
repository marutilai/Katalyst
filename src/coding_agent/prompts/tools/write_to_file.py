from textwrap import dedent

WRITE_TO_FILE_PROMPT = dedent("""
# write_to_file Tool

Description: Use this tool to write the full content to a file. If the file exists, it will be overwritten; if not, it will be created (including any needed directories). Always provide the complete intended content—no truncation or omissions.

## Parameters for 'action_input' object:
- path: (string, required) File path to write (relative to workspace)
- content: (string, required) The full content to write (no line numbers, just the file content)

## Example of how to structure your JSON response to use this tool:
{
  "thought": "I want to create a new frontend config file.",
  "action": "write_to_file",
  "action_input": {
    "path": "frontend-config.json",
    "content": "{\n  \"apiEndpoint\": \"https://api.example.com\",\n  ...\n}"
  }
}

## Tool Output Format (Observation):
The tool will return a JSON string as its observation. This JSON object will have the following keys:
- 'success': (boolean) True if the file was written successfully, False otherwise.
- 'path': (string) The absolute file path that was written.
- 'info': (string, optional) A success message if the file was written.
- 'error': (string, optional) An error message if something went wrong (e.g., invalid path, syntax error, write error).
- 'cancelled': (boolean, optional) True if the user declined to write the file.

## Example Tool Outputs (Observation JSON):

Example 1: Successful write:
{
  "success": true,
  "path": "/absolute/path/to/frontend-config.json",
  "info": "Successfully wrote to file: /absolute/path/to/frontend-config.json"
}

Example 2: User declined to write:
{
  "success": false,
  "path": "/absolute/path/to/frontend-config.json",
  "cancelled": true,
  "info": "User declined to write file."
}

Example 3: Syntax error in Python file:
{
  "success": false,
  "path": "/absolute/path/to/script.py",
  "error": "Error: Some problems were found in the content you were trying to write to 'script.py'. Here are the problems found for 'script.py': invalid syntax (script.py, line 2) Please fix the problems and try again."
}

Example 4: Invalid path:
{
  "success": false,
  "path": "",
  "error": "No valid 'path' provided."
}
""")
