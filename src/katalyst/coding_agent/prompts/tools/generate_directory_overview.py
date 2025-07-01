from textwrap import dedent

GENERATE_DIRECTORY_OVERVIEW_TOOL_PROMPT = dedent("""
# generate_directory_overview Tool

Description: Generate a tree-like overview of a directory structure.

Parameters:
- dir_path: (string, required) Directory path to analyze
- respect_gitignore: (boolean, optional) Whether to respect .gitignore rules

Output: Tree-formatted directory structure
""")