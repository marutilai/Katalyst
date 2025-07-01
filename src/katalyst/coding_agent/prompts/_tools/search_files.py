from textwrap import dedent

SEARCH_FILES_PROMPT = dedent("""
# regex_search_inside_files Tool

Description: Search INSIDE file contents using regex patterns across files in a directory. Provides context-rich results with file names and line numbers.

## When to Use:
- Finding code patterns or text within files
- Locating TODO comments inside code  
- Finding where functions/classes are defined
- Searching for configuration values in files
- Finding which files contain specific imports

## Parameters:
- path: (string, required) Directory to search (recursive) - use absolute path from project root, e.g., 'project_folder/subfolder'
- regex: (string, required) Regular expression pattern (Rust regex syntax)
- file_pattern: (string, optional) Glob pattern to filter files (e.g., '*.py', '*.{js,ts}')

## Example:
{
  "thought": "I want to find all TODO comments in Python files.",
  "action": "regex_search_inside_files",
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
- Success: {"matches": [{"file": "project_folder/module/file.py", "line": 12, "content": "# TODO: Refactor this function"}]}
- No matches: {"matches": [], "info": "No matches found"}
- Error: {"error": "Directory not found: ./missing_dir"}
""")