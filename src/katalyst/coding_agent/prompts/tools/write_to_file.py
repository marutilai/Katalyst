from textwrap import dedent

WRITE_TO_FILE_PROMPT = dedent("""
# write_to_file Tool

Description: Write full content to a file. Overwrites existing files or creates new ones with directories.

## When to Use:
- Creating new configuration files
- Writing generated code or templates
- Saving analysis results or reports
- Creating documentation files
- Duplicating files to new locations
- Initializing project structure files

## Parameters:
- path: (string, required) File path to write
- content: (string, required) Full file content - NO truncation
- line_count: (integer, REQUIRED with content) Count ALL lines including empty ones
- content_ref: (string, optional) Use this from read_file instead of content for exact copies
- auto_approve: (boolean, optional) Skip user confirmation

## CRITICAL Rules:
1. When using content: ALWAYS provide line_count (prevents truncation errors)
2. For file copies: Use content_ref from read_file, NOT content
3. Use EXACT content_ref value - don't modify it

## Example:
{
  "thought": "Create config with 3 lines",
  "action": "write_to_file",
  "action_input": {
    "path": "config.json",
    "content": "{\\n  \"api\": \"key\"\\n}",
    "line_count": 3
  }
}

## Output: JSON with success, path, and optional error/info/cancelled
""")
