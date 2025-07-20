from textwrap import dedent

LIST_CODE_DEFINITION_NAMES_TOOL_PROMPT = dedent("""
# list_code_definition_names Tool

Description: List all code definitions (classes, functions, methods) in source files using tree-sitter.

Parameters:
- path: (string, required) File path or directory to analyze
- auto_approve: (boolean, optional) Skip confirmation prompts (default: True)

Output: JSON with keys:
- files: List of file results, each containing:
  - file: File path
  - definitions: List of code definitions with type, name, line
  - info: Informational message (if applicable)
  - error: Error message (if parsing failed)
- error: Error message (if operation failed)

Examples:
- list_code_definition_names("main.py")     # Analyze single file
- list_code_definition_names("src/")        # Analyze all files in directory
""")