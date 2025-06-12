from textwrap import dedent

# Tool-level description and usage notes for summarize_code_structure
SUMMARIZE_CODE_STRUCTURE_PROMPT = dedent("""
# summarize_code_structure Tool

Description: Provides a high-level, "big picture" analysis of a codebase by scanning a directory, summarizing each source file, and creating a final overall summary. It is the most efficient tool for understanding the purpose and architecture of multiple files at once. The tool recursively scans a path, summarizes each file, and provides an overall architectural summary.

## When to Use This Tool:
- When the task is to understand or document an entire project, module, or large directory.
- When you need to quickly get up to speed on a new codebase.
- When you need to generate documentation or architectural overviews.

## When NOT to Use This Tool:
- **For reading the content of a single file for the purpose of making a small edit.** For that, use the `read_file` tool, which is more direct.
                                         
## IMPORTANT USAGE NOTE
- You ONLY need to provide the 'path' to the file or directory. The tool will handle reading the file content internally. **DO NOT** pass the file content yourself using a 'context' or 'file_content' argument.
- **ALWAYS call this tool on a top-level directory (e.g., 'src/', 'app/') instead of on individual files.**
- The tool is designed to be called **ONCE** per major directory to get a comprehensive overview.

## Parameters for 'action_input' object:
- path: (string, required) The path of the file or directory to summarize.
- respect_gitignore: (boolean, optional) If true, .gitignore patterns will be respected when scanning a directory. Defaults to true.
""")
