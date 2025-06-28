from textwrap import dedent

LIST_CODE_DEFINITION_NAMES_PROMPT = dedent("""
# list_code_definition_names Tool

Description: List code definitions (classes, functions, methods) from a source file or all top-level files in a directory.

## Parameters:
- path: (string, required) File or directory path to analyze

## Example:
{
  "thought": "I need to see all function and class definitions in this file.",
  "action": "list_code_definition_names",
  "action_input": {
    "path": "project_folder/module/file.py"
  }
}

## Output Format:
JSON with keys: 'files' (list), 'error' (optional)

Each file object: {'file': 'filename', 'definitions': [{'type': 'function|class|method', 'name': 'name', 'line': line_number}], 'info' (optional), 'error' (optional)}

Example outputs:
- Success: {"files": [{"file": "project_folder/module/file.py", "definitions": [{"type": "function", "name": "example_function", "line": 10}]}]}
- No definitions: {"files": [{"file": "project_folder/module/empty.py", "definitions": [], "info": "No definitions found"}]}
- Error: {"error": "Path not found: project_folder/module/missing.py"}
""")
