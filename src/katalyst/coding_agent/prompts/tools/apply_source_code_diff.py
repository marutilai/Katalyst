from textwrap import dedent

APPLY_SOURCE_CODE_DIFF_PROMPT = dedent('''
# apply_source_code_diff Tool

Description: Apply precise code changes using search/replace diff format. Use read_file first to get exact content and line numbers.

## When to Use:
- Making precise edits to existing code
- Refactoring specific functions or methods
- Updating configuration values
- Fixing bugs with surgical precision

## Parameters:
- path: (string, required) File path to modify
- diff: (string, required) Search/replace blocks defining changes
- auto_approve: (boolean, optional) Skip user confirmation if true

## Diff Format - CRITICAL: "-------" IS REQUIRED:
<<<<<<< SEARCH
:start_line:<line number>
-------
[exact content to find]
=======
[new content to replace with]
>>>>>>> REPLACE

⚠️ MUST HAVE "-------" AFTER :start_line: OR IT WILL FAIL

## Example:
{
  "action": "apply_source_code_diff",
  "action_input": {
    "path": "file.py",
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
JSON with: path, success (bool), info/error (optional)
- Success: {"path": "file.py", "success": true, "info": "Successfully applied diff"}
- Error: {"path": "file.py", "success": false, "error": "Missing '-------' separator"}

Note: Fuzzy matching searches ±20 lines if exact match fails
''')
