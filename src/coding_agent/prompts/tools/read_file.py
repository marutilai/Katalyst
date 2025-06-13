from textwrap import dedent

READ_FILE_TOOL_PROMPT = dedent("""
# read_file Tool

Description: Use this tool to read the contents of a single, specific file. This is your primary tool for focused tasks like understanding the logic of one file, preparing to make a specific edit, or debugging. By default, you should read the entire file unless you have a strong reason to suspect it is extremely large (e.g., many megabytes) AND you only need a small, specific section. If you do read in chunks using 'start_line' and 'end_line', be systematic in your 'thought' process to track progress and ensure you cover the necessary parts or the entire file if needed for the sub-task. Do not use this tool for binary files.

## When to Use This Tool:
- When you need the exact, full content of a known file to plan a change.
- When you are working on a sub-task that involves modifying a single file.
- For reading non-code files like README.md, package.json, or pyproject.toml.
                                                              
## Parameters for 'action_input' object:
- path: (string, required) File path to read (relative to workspace)
- start_line: (integer, optional) Starting line number (1-based, inclusive). Only use if you need a specific section.
- end_line: (integer, optional) Ending line number (1-based, inclusive). Only use if you need a specific section.

## Example of how to structure your JSON response to use this tool:
{
  "thought": "I need to read the entire 'src/utils.py' to understand its functionality.",
  "action": "read_file",
  "action_input": {
    "path": "src/utils.py"
  }
}

Example of reading a specific section (only when necessary):
{
  "thought": "I need to check the imports at the top of 'src/utils.py' to understand its dependencies.",
  "action": "read_file",
  "action_input": {
    "path": "src/utils.py",
    "start_line": 1,
    "end_line": 10
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

Example 1: Successful read of entire file:
{
  "path": "/absolute/path/to/src/utils.py",
  "start_line": 1,
  "end_line": 50,
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
