from textwrap import dedent

SEARCH_FILES_PROMPT = dedent("""
# search_files Tool

Use this tool to perform a regex search across files in a directory. The search is recursive and can be filtered by file pattern. Results include context for each match.

Parameters:
- path: (required) Directory to search (relative to workspace)
- regex: (required) Regex pattern to search for (Rust regex syntax)
- file_pattern: (optional) Glob pattern to filter files (e.g., '*.ts')

## Usage
<search_files>
<path>Directory path here</path>
<regex>Your regex pattern here</regex>
<file_pattern>Optional file pattern</file_pattern>
</search_files>

## Example
<search_files>
<path>.</path>
<regex>.*</regex>
<file_pattern>*.ts</file_pattern>
</search_files>
""") 