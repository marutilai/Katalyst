from textwrap import dedent

GLOB_TOOL_PROMPT = dedent("""
# glob Tool

Description: Find files matching glob patterns.

Parameters:
- pattern: (string, required) Glob pattern (* = any chars, ** = recursive, ? = one char, [...] = set)
- path: (string, optional) Base directory to search from (default: current)
- respect_gitignore: (boolean, optional) Filter gitignored files (default: True)

Output: JSON with keys:
- pattern: The glob pattern used
- base_path: The base directory searched
- files: List of matching file paths (relative to base_path)
- info: Additional information (e.g., if results were truncated or no matches found)
- error: Error message if the operation failed

Examples:
- glob("*.py")          # Python files in current dir
- glob("**/*.py")       # Python files recursively  
- glob("src/**/*.tsx")  # TSX files under src/
- glob("[A-Z]*.md")               # Markdown files starting with uppercase
- glob("data/????.csv")           # CSV files with 4-character names
Notes:
- Use ** for recursive search
- Limited to 100 results
""")