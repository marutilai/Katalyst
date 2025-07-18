from textwrap import dedent

LS_TOOL_PROMPT = dedent("""
# ls Tool

Description: List directory contents, similar to the Unix ls command.

Parameters:
- path: (string, optional) Directory to list (default: current directory ".")
- all: (boolean, optional) Show hidden files starting with . (like ls -a, default: False)
- long: (boolean, optional) Use long listing format with details (like ls -l, default: False)
- recursive: (boolean, optional) List subdirectories recursively (like ls -R, default: False)
- human_readable: (boolean, optional) Show sizes in human readable format (default: True)
- respect_gitignore: (boolean, optional) Respect .gitignore patterns (default: True)

Output: JSON with keys:
- path: The directory being listed
- entries: List of entries, each containing:
  - name: File/directory name (directories end with /)
  - type: "file" or "dir"
  - size: File size (only in long format)
  - permissions: Unix permissions (only in long format)
  - modified: Last modification time (only in long format)

Examples:
- ls()  # List current directory
- ls("src/")  # List src directory
- ls(all=True)  # Show hidden files
- ls(long=True)  # Detailed listing with sizes and permissions
- ls(recursive=True)  # List all subdirectories
- ls("src/", long=True, all=True)  # Detailed listing including hidden files

Notes:
- Directories are marked with trailing /
- Hidden files (starting with .) are excluded by default
- Respects .gitignore patterns by default
- Human readable sizes use K/M/G suffixes
""")