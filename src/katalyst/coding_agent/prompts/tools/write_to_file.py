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
- If you have a content_ref from read_file, ALWAYS use it instead of content parameter
- Use the EXACT content_ref value from the observation - do NOT create or modify reference IDs
- This ensures exact content preservation when copying or duplicating files
- Check your previous observations for the exact content_ref before using write_to_file

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
  "thought": "I read README.md and the observation included a content_ref. I'll use this exact reference to create a copy.",
  "action": "write_to_file",
  "action_input": {
    "path": "README_copy.md",
    "content_ref": "{exact_content_ref_from_read_file_observation}"
  }
}

## Output Format:
JSON with keys: 'success' (boolean), 'path', 'info' (optional), 'error' (optional), 'cancelled' (optional)

Example outputs:
- Success: {"success": true, "path": "/path/to/file.json", "info": "Successfully wrote to file"}
- Declined: {"success": false, "path": "/path/to/file.json", "cancelled": true, "info": "User declined"}
- Error: {"success": false, "path": "/path/to/file.py", "error": "Syntax error in content"}
""")
