from textwrap import dedent

GENERATE_DIRECTORY_OVERVIEW_REDUCE_PROMPT = dedent("""
# generate_directory_overview (Reduce Step)

Description: Given a set of file summaries, produce an overall summary of the codebase's purpose, architecture, and main components. Identify the most important files, classes, or modules.

## Input
- File summaries: {docs}

## Output Format
Return a JSON object with the following keys:
- overall_summary: (string) A concise summary of the codebase's purpose, architecture, and main components
- main_components: (list of strings) The most important files, classes, or modules

## Example Output
{
  "overall_summary": "The application is a command-line agent with a REPL interface...",
  "main_components": ["src/app/main.py", "src/katalyst_core/graph.py"]
}
""")
