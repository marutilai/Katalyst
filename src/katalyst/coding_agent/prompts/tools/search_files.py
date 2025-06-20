from textwrap import dedent

SEARCH_FILES_PROMPT = dedent("""
# regex_search_files Tool

Search for regex patterns across files in a directory. Provides context-rich results with file names and line numbers.

## Parameters:
- path: (string, required) Directory to search (recursive)
- regex: (string, required) Regular expression pattern (Rust regex syntax)
- file_pattern: (string, optional) Glob pattern to filter files (e.g., '*.ts')

## Example:
{
  "thought": "I want to find all TODO comments in the codebase.",
  "action": "regex_search_files",
  "action_input": {
    "path": ".",
    "regex": "TODO"
  }
}

## Output Format:
JSON with keys: 'matches' (list), 'info' (optional), 'error' (optional)

Each match object: {'file': 'filename', 'line': line_number, 'content': 'line content'}

Example outputs:
- Success: {"matches": [{"file": "src/utils.py", "line": 12, "content": "# TODO: Refactor"}]}
- No matches: {"matches": [], "info": "No matches found"}
- Error: {"error": "Directory not found: ./missing_dir"}
""")
