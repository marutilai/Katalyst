from textwrap import dedent

WRITE_TO_FILE_PROMPT = dedent("""
# write_to_file Tool

Use this tool to write the full content to a file. If the file exists, it will be overwritten; if not, it will be created (including any needed directories). Always provide the complete intended content—no truncation or omissions.

## Parameters:
- path: (required) File path to write (relative to workspace)
- content: (required) The full content to write (no line numbers, just the file content)

## Usage
<write_to_file>
<path>File path here</path>
<content>
Your file content here
</content>
</write_to_file>

## Example
<write_to_file>
<path>frontend-config.json</path>
<content>
{
  "apiEndpoint": "https://api.example.com",
  "theme": {
    "primaryColor": "#007bff",
    "secondaryColor": "#6c757d",
    "fontFamily": "Arial, sans-serif"
  },
  "features": {
    "darkMode": true,
    "notifications": true,
    "analytics": false
  },
  "version": "1.0.0"
}
</content>
</write_to_file>
""")
