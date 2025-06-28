from textwrap import dedent

APPLY_SOURCE_CODE_DIFF_PROMPT = dedent('''
# apply_source_code_diff Tool

Description: Apply precise code changes using search/replace diff format. Use read_file first to get exact content and line numbers. Can batch multiple changes in one request.

## When to Use:
- Making precise edits to existing code
- Refactoring specific functions or methods
- Updating configuration values
- Fixing bugs with surgical precision
- Batch editing multiple sections of a file

## Parameters:
- path: (string, required) File path to modify
- diff: (string, required) Search/replace blocks defining changes
- auto_approve: (boolean, optional) Skip user confirmation if true

## Diff Format:
<<<<<<< SEARCH
:start_line:<line number>
-------
[exact content to find, including whitespace]
=======
[new content to replace with]
>>>>>>> REPLACE

## Example:
{
  "thought": "I need to update the return value of foo function.",
  "action": "apply_source_code_diff",
  "action_input": {
    "path": "project_folder/module/file.py",
    "diff": """<<<<<<< SEARCH
:start_line:10
-------
def foo():
    return 1
=======
def foo():
    return 2
>>>>>>> REPLACE"""
  }
}

## Output Format:
JSON with keys: 'path', 'success' (boolean), 'info' (optional), 'error' (optional)

Example outputs:
- Success: {"path": "project_folder/module/file.py", "success": true, "info": "Successfully applied diff"}
- Error: {"path": "project_folder/module/file.py", "success": false, "error": "Search block does not match"}
- Declined: {"path": "project_folder/module/file.py", "success": false, "info": "User declined to apply diff"}
''')
