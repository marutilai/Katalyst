from textwrap import dedent

SUMMARIZE_CODE_STRUCTURE_PROMPT = dedent("""
# summarize_code_structure Tool

Description: Use this tool for high-level, "big picture" analysis of a codebase. It is most effective when you need to understand the purpose of an entire directory or multiple files at once. The tool recursively scans a path, summarizes each file, and provides an overall architectural summary.

## When to Use This Tool:
- When the task is to understand or document an entire project, module, or large directory.
- When you need to quickly get up to speed on a new codebase.
- When you need to generate documentation or architectural overviews.

## When NOT to Use This Tool:
- **For reading the content of a single file for the purpose of making a small edit.** For that, use the `read_file` tool, which is more direct.
                                         
## IMPORTANT USAGE NOTE
You ONLY need to provide the 'path' to the file or directory. The tool will handle reading the file content internally. **DO NOT** pass the file content yourself using a 'context' or 'file_content' argument.

## Parameters for 'action_input' object:
- path: (string, required) The path of the file or directory to summarize.
- respect_gitignore: (boolean, optional) If true, .gitignore patterns will be respected when scanning a directory. Defaults to true.

## Example of how to structure your JSON response to use this tool:
{
  "thought": "I need to get a high-level overview of the 'src/app' directory.",
  "action": "summarize_code_structure",
  "action_input": {
    "path": "src/app"
  }
}

## Tool Output Format (Observation):
The tool will return a JSON string as its observation. This JSON object will have the following keys:
- 'summaries': (list of dicts) A list of individual file summary objects.
- 'overall_summary': (string, optional) An AI-generated summary of the entire codebase's purpose and architecture.
- 'main_components': (list of strings, optional) A list of key files or modules identified by the AI.
- 'error': (string, optional) An error message if something went wrong (e.g., path not found).

## Example Tool Outputs (Observation JSON):

Example 1: Successful summary:
{
  "summaries": [
    {
      "file_path": "src/app/main.py",
      "summary": "This file contains the main entry point and REPL loop for the application.",
      "key_classes": [],
      "key_functions": ["main", "repl"]
    }
  ],
  "overall_summary": "The application is a command-line agent with a REPL interface...",
  "main_components": ["src/app/main.py", "src/katalyst_core/graph.py"]
}

Example 2: Path not found:
{
  "error": "Path not found: src/non_existent_dir"
}
""")
