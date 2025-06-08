from textwrap import dedent

LIST_CODE_DEFINITION_NAMES_PROMPT = dedent("""
# list_code_definition_names Tool

Description: Use this tool to list code definitions (classes, functions, methods, etc.) from a source file or all files at the top level of a specified directory. This helps you understand the codebase structure and important constructs.

## Parameters for 'action_input' object:
- path: (string, required) The path of the file or directory (relative to the workspace) to analyze. When given a directory, it lists definitions from all top-level source files.

## Example of how to structure your JSON response to use this tool:
{
  "thought": "I need to see all function and class definitions in 'src/utils.py'.",
  "action": "list_code_definition_names",
  "action_input": {
    "path": "src/utils.py"
  }
}

Another example, for a directory:
{
  "thought": "I want to see all top-level code definitions in the 'src/' directory.",
  "action": "list_code_definition_names",
  "action_input": {
    "path": "src/"
  }
}

## Tool Output Format (Observation):
The tool will return a JSON string as its observation. This JSON object will have the following keys:
- 'files': (list) Each item is an object with:
    - 'file': (string) The file name.
    - 'definitions': (list) Each item is an object with:
        - 'type': (string) The type of definition (e.g., 'function', 'class', 'method').
        - 'name': (string) The name of the definition.
        - 'line': (integer) The line number where the definition starts.
    - 'info': (string, optional) If no definitions were found in the file.
    - 'error': (string, optional) If an error occurred for this file.
- 'error': (string, optional) If a global error occurred (e.g., path not found).

## Example Tool Outputs (Observation JSON):

Example 1: Successful listing from a file:
{
  "files": [
    {
      "file": "src/utils.py",
      "definitions": [
        {"type": "function", "name": "foo", "line": 10},
        {"type": "class", "name": "Bar", "line": 20}
      ]
    }
  ]
}

Example 2: Directory with multiple files:
{
  "files": [
    {
      "file": "src/utils.py",
      "definitions": [
        {"type": "function", "name": "foo", "line": 10}
      ]
    },
    {
      "file": "src/other.py",
      "definitions": [],
      "info": "No definitions found."
    }
  ]
}

Example 3: File with a parse error:
{
  "files": [
    {
      "file": "src/bad.py",
      "definitions": [],
      "error": "Syntax error in file."
    }
  ]
}

Example 4: Global error (path not found):
{
  "error": "Path not found: src/does_not_exist.py"
}
""")
