from textwrap import dedent

LS_TOOL_PROMPT = dedent("""
# ls Tool

Description: List directory contents.

Parameters:
- path: (string, optional) Directory to list (default: current)
- all: (boolean, optional) Show hidden files (default: False)
- long: (boolean, optional) Detailed format with size/permissions (default: False)
- recursive: (boolean, optional) List subdirectories recursively (default: False)
- human_readable: (boolean, optional) Human readable sizes (default: True)
- respect_gitignore: (boolean, optional) Filter gitignored files (default: True)

Output: JSON with keys:
- path: The directory being listed
- entries: List of entries, each containing:
  - name: File/directory name (directories end with /)
  - type: "file" or "dir"
  - size: File size (only in long format)
  - permissions: Unix permissions (only in long format)
  - modified: Last modification time (only in long format)

Examples:
- ls()                    # List current directory
- ls("src/", long=True)   # Detailed listing of src/
- ls(all=True, recursive=True)  # Show all files recursively

Notes:
- Directories end with /
- Lists both files and directories
""")