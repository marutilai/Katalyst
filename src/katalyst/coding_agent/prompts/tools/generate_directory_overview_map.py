from textwrap import dedent

GENERATE_DIRECTORY_OVERVIEW_MAP_PROMPT = dedent("""
# generate_directory_overview (Map Step)

Description: Summarize the purpose, main logic, and key components of a single code file. Identify important classes and functions.

## Input
- File content: {context}

## Output Format
JSON object with keys:
- file_path: (string) File being summarized
- summary: (string) Concise summary of file's purpose and main logic
- key_classes: (list of strings) Important class names
- key_functions: (list of strings) Important function names

## Example
{
  "file_path": "project_folder/module/filename.py",
  "summary": "Brief description of what this file does and its main purpose.",
  "key_classes": ["ExampleClass", "AnotherClass"],
  "key_functions": ["process_data", "validate_input"]
}
""")
