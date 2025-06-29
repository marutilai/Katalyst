from textwrap import dedent

WRITE_TO_FILE_PROMPT = dedent("""
# write_to_file Tool

Description: Write full content to a file. Overwrites existing files completely or creates new files (including directories). Provide complete content—no truncation.

## When to Use:
- Creating new files or replacing file contents entirely
- Setting up project structure (creates parent directories automatically)
- Writing configuration files, scripts, or documentation
- Saving generated output or results
- Creating empty marker files like __init__.py

## Parameters:
- path: (string, required) File path to write (use absolute path from project root, e.g., 'project_folder/subfolder/file.ext')
- content: (string, required) Full file content - Partial updates or placeholders like '// rest of code unchanged' are STRICTLY FORBIDDEN.
- content_ref: (string, optional) Use this from read_file instead of content for exact copies
- auto_approve: (boolean, optional) Skip user confirmation if True

## CRITICAL Rules:
1. For file copies: Use content_ref from read_file, NOT content
2. Use EXACT content_ref value - don't modify it

## Example:
{
  "thought": "Create config file",
  "action": "write_to_file",
  "action_input": {
    "path": "config.json",
    "content": "{\\n  \"api\": \"key\"\\n}"
  }
}

## Output Format:
JSON with keys: 'success' (boolean), 'path', 'info' (optional), 'error' (optional), 'cancelled' (optional)
""")
