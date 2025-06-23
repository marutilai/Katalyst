from textwrap import dedent

WRITE_TO_FILE_PROMPT = dedent("""
# write_to_file Tool

Description: Write full content to a file. Overwrites existing files or creates new ones (including directories). Provide complete content—no truncation.

## When to Use:
- Creating new files or replacing file contents entirely
- Setting up project structure (creates parent directories automatically)
- Writing configuration files, scripts, or documentation
- Saving generated output or results
- Creating empty marker files like __init__.py

## Parameters:
- path: (string, required) File path to write
- content: (string, required) Full content to write
- content_ref: (string, optional) Reference to content from read_file (use instead of content)
- auto_approve: (boolean, optional) Skip user confirmation if true

## IMPORTANT: Content Reference System
When you read a file using read_file, it returns a "content_ref" field. You should use this reference
instead of copying the content directly to avoid hallucination or corruption by the LLM:
- If you have a content_ref from read_file, use it instead of content
- This ensures exact content preservation when copying or duplicating files

## Examples:

### Example 1: Creating new content
{
  "thought": "I want to create a new config file.",
  "action": "write_to_file",
  "action_input": {
    "path": "config.json",
    "content": "{\\n  \"apiEndpoint\": \"https://api.example.com\"\\n}"
  }
}

### Example 2: Using content reference (preferred for file copies)
{
  "thought": "I read README.md and got content_ref 'ref:README.md:a1b2c3d4'. I'll use this reference to create an exact copy.",
  "action": "write_to_file",
  "action_input": {
    "path": "README_copy.md",
    "content_ref": "ref:README.md:a1b2c3d4"
  }
}

## Output Format:
JSON with keys: 'success' (boolean), 'path', 'info' (optional), 'error' (optional), 'cancelled' (optional)

Example outputs:
- Success: {"success": true, "path": "/path/to/file.json", "info": "Successfully wrote to file"}
- Declined: {"success": false, "path": "/path/to/file.json", "cancelled": true, "info": "User declined"}
- Error: {"success": false, "path": "/path/to/file.py", "error": "Syntax error in content"}
""")
