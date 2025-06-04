from textwrap import dedent

SEARCH_FILES_PROMPT = dedent("""
# regex_search_files Tool

Description: Use this tool to perform a regex search across files in a specified directory, providing context-rich results. This tool searches for patterns or specific content across multiple files, displaying each match with file name and line number.

## Parameters for 'action_input' object:
- path: (string, required) The path of the directory to search in (relative to the workspace). This directory will be recursively searched.
- regex: (string, required) The regular expression pattern to search for. Uses Rust regex syntax.
- file_pattern: (string, optional) Glob pattern to filter files (e.g., '*.ts' for TypeScript files). If not provided, it will search all files (*).

## Example of how to structure your JSON response to use this tool:
{
  "thought": "I want to find all TODO comments in the codebase.",
  "action": "regex_search_files",
  "action_input": {
    "path": ".",
    "regex": "TODO"
  }
}

Another example, searching only TypeScript files:
{
  "thought": "I want to find all function definitions in TypeScript files.",
  "action": "regex_search_files",
  "action_input": {
    "path": ".",
    "regex": "function ",
    "file_pattern": "*.ts"
  }
}

## Tool Output Format (Observation):
The tool will return a JSON string as its observation. This JSON object will have the following keys:
- 'matches': (list) Each item is an object with:
    - 'file': (string) The file name where the match was found.
    - 'line': (integer or string) The line number of the match.
    - 'content': (string) The line content where the match was found.
- 'info': (string, optional) If no matches were found or results were truncated.
- 'error': (string, optional) If something went wrong (e.g., directory not found, rg not installed).

## Example Tool Outputs (Observation JSON):

Example 1: Successful search with matches:
{
  "matches": [
    {"file": "src/utils.py", "line": 12, "content": "# TODO: Refactor this function"},
    {"file": "src/main.py", "line": 45, "content": "# TODO: Add error handling"}
  ]
}

Example 2: No matches found:
{
  "matches": [],
  "info": "No matches found for pattern 'TODO' in ."
}

Example 3: Results truncated:
{
  "matches": [ ... ],
  "info": "Results truncated at 1000 matches."
}

Example 4: Directory not found:
{
  "error": "Directory not found: ./missing_dir"
}

Example 5: ripgrep not installed:
{
  "error": "'rg' (ripgrep) is not installed."
}
""") 