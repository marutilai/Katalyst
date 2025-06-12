from textwrap import dedent

GENERATE_DIRECTORY_OVERVIEW_MAP_PROMPT = dedent("""
# generate_directory_overview (Map Step)

Description: Summarize the purpose, main logic, and key components of a single code file. Identify and list any important classes and functions.

## Input
- File content: {context}

## Output Format
Return a JSON object with the following keys:
- file_path: (string) The file being summarized
- summary: (string) A concise summary of the file's purpose and main logic
- key_classes: (list of strings) Names of important classes, if any
- key_functions: (list of strings) Names of important functions, if any

## Example Output
{
  "file_path": "src/app/main.py",
  "summary": "This file contains the main entry point and REPL loop for the application.",
  "key_classes": [],
  "key_functions": ["main", "repl"]
}
""")
