from textwrap import dedent

APPLY_SOURCE_CODE_DIFF_PROMPT = dedent('''
# apply_source_code_diff Tool

Apply precise code changes using search/replace diff format. Use read_file first to get exact content and line numbers. Can batch multiple changes in one request.

## Parameters:
- path: (string, required) File path to modify
- diff: (string, required) Search/replace blocks defining changes

## Diff Format:
<<<<<<< SEARCH
:start_line:<line number>
-------
[exact content to find]
=======
[new content to replace with]
>>>>>>> REPLACE

## Example:
"action_input": {
  "path": "src/utils.py",
  "diff": """
<<<<<<< SEARCH
:start_line:10
-------
def foo():
    return 1
=======
def foo():
    return 2
>>>>>>> REPLACE
"""
}

## Output Format:
JSON with keys: 'path', 'success' (boolean), 'info' (optional), 'error' (optional)

Example outputs:
- Success: {"path": "src/utils.py", "success": true, "info": "Successfully applied diff"}
- Error: {"path": "src/utils.py", "success": false, "error": "Search block does not match"}
- Declined: {"path": "src/utils.py", "success": false, "info": "User declined to apply diff"}
''')
