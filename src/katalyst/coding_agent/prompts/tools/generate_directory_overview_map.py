from textwrap import dedent

GENERATE_DIRECTORY_OVERVIEW_MAP_PROMPT = dedent("""
# generate_directory_overview (Map Step)

Summarize the purpose, main logic, and key components of a single code file. Identify important classes and functions.

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
  "file_path": "src/app/main.py",
  "summary": "Main entry point and REPL loop for the application.",
  "key_classes": [],
  "key_functions": ["main", "repl"]
}
""")
