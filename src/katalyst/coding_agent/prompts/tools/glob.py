from textwrap import dedent

GLOB_TOOL_PROMPT = dedent("""
# glob Tool

Description: Find files matching glob patterns. Efficient way to locate files by name patterns across directory structures.

Parameters:
- pattern: (string, required) Glob pattern to match files
- path: (string, optional) Base directory to search from (default: current directory)
- respect_gitignore: (boolean, optional) Whether to filter out gitignored files (default: True)

Output: JSON with keys:
- pattern: The glob pattern used
- base_path: The base directory searched
- files: List of matching file paths (relative to base_path)
- info: Additional information (e.g., if results were truncated or no matches found)
- error: Error message if the operation failed

Glob Pattern Syntax:
- * matches any number of characters (except /)
- ** matches any number of directories recursively
- ? matches exactly one character
- [abc] matches any character in the set
- [a-z] matches any character in the range

Examples:
- glob("*.py")                    # All Python files in current directory
- glob("**/*.py")                 # All Python files recursively
- glob("test_*.js")               # All JS files starting with test_
- glob("src/**/*.tsx")            # All TSX files under src/
- glob("**/node_modules/")        # Find all node_modules directories
- glob("[A-Z]*.md")               # Markdown files starting with uppercase
- glob("data/????.csv")           # CSV files with 4-character names

Notes:
- Use ** for recursive search through subdirectories
- Patterns are case-sensitive
- Results are sorted alphabetically for consistency
- Limited to 100 results to prevent overwhelming output
- Directories are excluded unless pattern explicitly ends with /
- Respects .gitignore by default (use respect_gitignore=False to include ignored files)

Comparison with other tools:
- Use glob to find files by name pattern
- Use grep to search content within files
- Use ls to list directory contents with details
""")