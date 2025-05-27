# Prompt for list_files tool
from textwrap import dedent

LIST_FILES_PROMPT = dedent("""
# list_files Tool

Use this tool to list files and directories in a given directory. Set `recursive` to true to list all contents recursively, or false for top-level only. Do not use this tool just to confirm file creation.

Parameters:
- path: (required) Directory path to list (relative to workspace)
- recursive: (required) true for recursive, false for top-level only

## Usage
<list_files>
<path>Directory path here</path>
<recursive>true or false</recursive>
</list_files>

## Example
<list_files>
<path>.</path>
<recursive>false</recursive>
</list_files>
""")
