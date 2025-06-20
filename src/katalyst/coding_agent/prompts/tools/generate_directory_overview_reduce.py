from textwrap import dedent

GENERATE_DIRECTORY_OVERVIEW_REDUCE_PROMPT = dedent("""
# generate_directory_overview (Reduce Step)

Given file summaries, produce overall summary of codebase's purpose, architecture, and main components. Identify most important files, classes, or modules.

## Input
- File summaries: {docs}

## Output Format
JSON object with keys:
- overall_summary: (string) Concise summary of codebase's purpose, architecture, and main components
- main_components: (list of strings) Most important files, classes, or modules

## Example
{
  "overall_summary": "The application is a command-line agent with a REPL interface...",
  "main_components": ["src/app/main.py", "src/katalyst_core/graph.py"]
}
""")
