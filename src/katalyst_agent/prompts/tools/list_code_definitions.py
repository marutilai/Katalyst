from textwrap import dedent

LIST_CODE_DEFINITION_NAMES_PROMPT = dedent("""
# list_code_definition_names Tool

Use this tool to list definition names (classes, functions, methods, etc.) from a source file or all top-level files in a directory. This helps you understand the codebase structure and key constructs.

Parameters:
- path: (required) Path to the file or directory (relative to workspace).

## Usage
<list_code_definition_names>
<path>File or directory path here</path>
</list_code_definition_names>

## Examples
1. List definitions from a file:
<list_code_definition_names>
<path>src/main.ts</path>
</list_code_definition_names>

2. List definitions from a directory:
<list_code_definition_names>
<path>src/</path>
</list_code_definition_names>
""")
