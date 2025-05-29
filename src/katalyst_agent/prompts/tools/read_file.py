from textwrap import dedent

READ_FILE_TOOL_PROMPT = dedent("""
# read_file Tool

Use this tool to read the contents of a file. You can specify start and end lines to read only a portion of the file. Output includes line numbers for easy reference. Do not use this tool for binary files.

Parameters:
- path: (required) File path to read (relative to workspace)
- start_line: (optional) Starting line number (1-based, inclusive)
- end_line: (optional) Ending line number (1-based, inclusive)

## Usage
<read_file>
<path>File path here</path>
<start_line>Optional start line</start_line>
<end_line>Optional end line</end_line>
</read_file>

## Examples
1. Read an entire file:
<read_file>
<path>frontend-config.json</path>
</read_file>

2. Read the first 1000 lines:
<read_file>
<path>logs/application.log</path>
<end_line>1000</end_line>
</read_file>

3. Read lines 500-1000:
<read_file>
<path>data/large-dataset.csv</path>
<start_line>500</start_line>
<end_line>1000</end_line>
</read_file>
                               
4. Reading a specific function in a source file:
<read_file>
<path>src/app.ts</path>
<start_line>46</start_line>
<end_line>68</end_line>
</read_file>
""")
