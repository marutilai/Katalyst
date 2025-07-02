from textwrap import dedent

APPLY_SOURCE_CODE_DIFF_TOOL_PROMPT = dedent("""
# apply_source_code_diff Tool

Description: Apply changes to an existing file using a diff format.

Parameters:
- path: (string, required) File path to modify
- diff: (string, required) Changes in diff format

Diff format:
<<<<<<< SEARCH
:start_line:<line_number>
-------
original code
=======
modified code
>>>>>>> REPLACE

Output: JSON with keys: 'path', 'success', 'error'
""")