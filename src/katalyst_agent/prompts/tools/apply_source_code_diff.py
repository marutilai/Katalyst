from textwrap import dedent

APPLY_SOURCE_CODE_DIFF_PROMPT = dedent('''
# apply_source_code_diff Tool

Description: Use this tool to apply precise, surgical code changes to a file using a search/replace diff format. You can batch multiple changes in a single request by including multiple SEARCH/REPLACE blocks. The tool will maintain proper indentation and formatting while making changes. Always use the read_file tool first to get the exact content and line numbers for your diff.

## Parameters for 'action_input' object:
- path: (string, required) The path of the file to modify (relative to the workspace).
- diff: (string, required) The search/replace block(s) defining the changes. See below for format.

## Diff format (for the 'diff' string):
Each block must follow this format:

<<<<<<< SEARCH
:start_line:<line number where the search block starts>
-------
[exact content to find, including whitespace]
=======
[new content to replace with]
>>>>>>> REPLACE

You can include multiple such blocks in a single diff string to batch edits.

## Example of how to structure 'action_input' in your JSON response:
For a single change to 'src/utils.py':
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

For multiple changes in one file:
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

<<<<<<< SEARCH
:start_line:20
-------
def bar():
    return 3
=======
def bar():
    return 4
>>>>>>> REPLACE
"""
}

## Tool Output Format (Observation):
The tool will return a JSON string as its observation. This JSON object will have the following keys:
- 'path': (string) The file path that was modified.
- 'success': (boolean) True if the diff was applied successfully, False otherwise.
- 'info': (string, optional) A success message if the diff was applied or the user declined.
- 'error': (string, optional) An error message if something went wrong (e.g., file not found, diff format error, search block mismatch, syntax error, write error).

## Example Tool Outputs (Observation JSON):

Example 1: Successful diff application:
{
  "path": "src/utils.py",
  "success": true,
  "info": "Successfully applied diff to file: src/utils.py"
}

Example 2: File not found:
{
  "path": "src/does_not_exist.py",
  "success": false,
  "error": "File not found: src/does_not_exist.py"
}

Example 3: Search block mismatch:
{
  "path": "src/utils.py",
  "success": false,
  "error": "Search block does not match file at line 10. Please use read_file to get the exact content and line numbers."
}

Example 4: User declined to apply diff:
{
  "path": "src/utils.py",
  "success": false,
  "info": "User declined to apply diff."
}

Example 5: Syntax error after applying diff:
{
  "path": "src/utils.py",
  "success": false,
  "error": "Syntax error after applying diff: invalid syntax (utils.py, line 12)"
}
''')
