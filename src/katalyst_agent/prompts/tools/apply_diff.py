from textwrap import dedent

APPLY_DIFF_PROMPT = dedent('''
# apply_diff Tool

Use this tool to surgically replace code in a file by specifying exact search and replacement blocks. Each block must match the file content exactly, including whitespace and indentation. If unsure, use the read_file tool first.

Parameters:
- path: (required) File path to modify (relative to workspace)
- diff: (required) One or more search/replace blocks

## Diff Block Format
```
<<<<<<< SEARCH
:start_line:<line_number>
-------
[exact content to find]
=======
[new content to replace with]
>>>>>>> REPLACE
```
- Use one block per change. Multiple blocks can be included in a single diff.
- :start_line: is the line number where the search block starts in the file.
- Only use a single line of '=======' between search and replacement.

## Example Usage
<apply_diff>
<path>src/example.py</path>
<diff>
Your search/replace blocks here
</diff>
</apply_diff>
''')
