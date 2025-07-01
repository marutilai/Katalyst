from textwrap import dedent

LIST_CODE_DEFINITION_NAMES_TOOL_PROMPT = dedent("""
# list_code_definition_names Tool

Description: List all code definitions (classes, functions, methods) in a file.

Parameters:
- path: (string, required) File path to analyze

Output: JSON with keys: 'definitions' (list of definition names and types), 'error'
""")