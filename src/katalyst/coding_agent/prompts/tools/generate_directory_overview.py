from textwrap import dedent

GENERATE_DIRECTORY_OVERVIEW_TOOL_PROMPT = dedent("""
# generate_directory_overview Tool

Description: Analyze and summarize all code files in a directory using AI.

Parameters:
- dir_path: (string, required) Directory path to analyze  
- respect_gitignore: (boolean, optional) Whether to respect .gitignore rules (default: True)

Output: JSON with keys:
- summaries: List of file summaries with path, purpose, key classes/functions
- overall_summary: Architectural overview of the codebase
- main_components: Most important files/modules
- error: Error message (if analysis failed)

Examples:
- generate_directory_overview(".")          # Analyze current directory
- generate_directory_xoverview("src/")       # Analyze src directory
- generate_directory_overview("/path/to/project")  # Analyze specific path
""")