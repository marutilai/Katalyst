from textwrap import dedent

SEARCH_FILES_PROMPT = dedent("""
# regex_search_files Tool

Description: Search for regex patterns across files in a directory. Provides context-rich results with file names and line numbers.

## When to Use:
- Finding specific code patterns or text across multiple files
- Locating TODO comments, FIXMEs, or other markers
- Finding function/class definitions or usages
- Searching for configuration values or constants
- Identifying files that contain specific imports or dependencies

## Parameters:
- path: (string, required) Directory to search (recursive)
- regex: (string, required) Regular expression pattern (Rust regex syntax)
- file_pattern: (string, optional) Glob pattern to filter files (e.g., '*.py', '*.{js,ts}')

## Example:
{
  "thought": "I want to find all TODO comments in Python files.",
  "action": "regex_search_files",
  "action_input": {
    "path": ".",
    "regex": "TODO",
    "file_pattern": "*.py"
  }
}

## Output Format:
JSON with keys: 'matches' (list), 'info' (optional), 'error' (optional)

Each match object: {'file': 'filename', 'line': line_number, 'content': 'line content'}

Example outputs:
- Success: {"matches": [{"file": "src/utils.py", "line": 12, "content": "# TODO: Refactor this function"}]}
- No matches: {"matches": [], "info": "No matches found"}
- Error: {"error": "Directory not found: ./missing_dir"}
""")