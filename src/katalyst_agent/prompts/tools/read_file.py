from textwrap import dedent

READ_FILE_TOOL_PROMPT = dedent("""
# read_file Tool

Description: Use this tool to read the contents of a file. You can specify start and end lines to read only a portion of the file. Output includes line numbers for easy reference. Do not use this tool for binary files.

## Parameters for 'action_input' object:
- path: (string, required) File path to read (relative to workspace)
- start_line: (integer, optional) Starting line number (1-based, inclusive)
- end_line: (integer, optional) Ending line number (1-based, inclusive)

## Example of how to structure your JSON response to use this tool:
{
  "thought": "I need to read the first 10 lines of 'src/utils.py' to see the imports.",
  "action": "read_file",
  "action_input": {
    "path": "src/utils.py",
    "start_line": 1,
    "end_line": 10
  }
}

Another example, reading the whole file:
{
  "thought": "I want to see the entire contents of 'frontend-config.json'.",
  "action": "read_file",
  "action_input": {
    "path": "frontend-config.json"
  }
}

## Tool Output Format (Observation):
The tool will return a JSON string as its observation. This JSON object will have the following keys:
- 'path': (string) The absolute file path that was read.
- 'start_line': (integer) The first line number read (1-based).
- 'end_line': (integer) The last line number read (inclusive).
- 'content': (string) The file content read (may be empty).
- 'info': (string, optional) If the file is empty or no lines in the specified range.
- 'error': (string, optional) If something went wrong (e.g., file not found, permission denied).

## Example Tool Outputs (Observation JSON):

Example 1: Successful read of lines 1-10:
{
  "path": "/absolute/path/to/src/utils.py",
  "start_line": 1,
  "end_line": 10,
  "content": "import os\nimport sys\n..."
}

Example 2: File not found:
{
  "error": "File not found: /absolute/path/to/missing.py"
}

Example 3: File is empty or no lines in range:
{
  "path": "/absolute/path/to/empty.txt",
  "start_line": 1,
  "end_line": 1,
  "info": "File is empty or no lines in specified range.",
  "content": ""
}
""")
