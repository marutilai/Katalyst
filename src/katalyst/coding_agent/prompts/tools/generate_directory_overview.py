from textwrap import dedent

# Tool-level description and usage notes for generate_directory_overview
GENERATE_DIRECTORY_OVERVIEW_PROMPT = dedent("""
# generate_directory_overview Tool

Description: Provides a high-level, "big picture" overview and documentation of a codebase by scanning a directory, summarizing each source file, and creating a final overall summary. It is the most efficient tool for understanding the purpose and architecture of multiple files at once. The tool recursively scans a directory, summarizes each file, and provides an overall architectural summary.

## When to Use This Tool:
- When the task is to understand or document an entire project, module, or large directory
- When you need to quickly get up to speed on a new codebase
- When you need to generate documentation or architectural overviews
- When you need to analyze the structure and relationships between files

## IMPORTANT USAGE NOTE
- You ONLY need to provide the 'dir_path' to the directory. The tool will handle reading all files internally.
- **ALWAYS call this tool on a top-level directory (e.g., 'src/', 'app/') to get a comprehensive overview.**
- The tool is designed to be called **ONCE** per major directory.
- **When called on a directory, it will recursively analyze all nested subdirectories and files. There is no need to call it again for subdirectories within the same parent directory.**
- The tool will automatically respect .gitignore patterns to avoid analyzing build artifacts, dependencies, etc.

## Parameters for 'action_input' object:
- dir_path: (string, required) The path of the directory to analyze. Must be a directory, not a file.
- respect_gitignore: (boolean, optional) If true, .gitignore patterns will be respected when scanning. Defaults to true.
""")
