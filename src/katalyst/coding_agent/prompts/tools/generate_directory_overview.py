from textwrap import dedent

# Tool-level description and usage notes for generate_directory_overview
GENERATE_DIRECTORY_OVERVIEW_PROMPT = dedent("""
# generate_directory_overview Tool

Provides high-level overview and documentation of a codebase by scanning a directory, summarizing each source file, and creating an overall summary. Most efficient for understanding multiple files at once.

## When to Use:
- Understand or document entire project, module, or large directory
- Get up to speed on new codebase quickly
- Generate documentation or architectural overviews
- Analyze structure and relationships between files

## IMPORTANT:
- Provide only 'dir_path' to directory. Tool handles file reading internally.
- Call on top-level directory (e.g., 'src/', 'app/') for comprehensive overview.
- Call ONCE per major directory. Recursively analyzes all nested content.
- Automatically respects .gitignore patterns.

## Parameters:
- dir_path: (string, required) Directory path to analyze (must be directory, not file)
- respect_gitignore: (boolean, optional) Respect .gitignore patterns. Defaults to true.
""")
