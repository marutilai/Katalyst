# coding_agent/prompts/tools/list_files.py
from textwrap import dedent

LIST_FILES_PROMPT = dedent("""
# list_files Tool

Description: Use this tool to list files and directories in a given directory. Set `recursive` to true to list all contents recursively, or false for top-level only. Do not use this tool just to confirm file creation.

## Parameters for 'action_input' object:
- path: (string, required) Directory path to list (relative to workspace).
- recursive: (boolean, required) `true` for recursive listing, `false` for top-level only.

## Example of how to structure 'action_input' in your JSON response:
If you decide to use this tool, the 'action_input' in your main JSON response for the ReAct step should be an object like this:

For a non-recursive listing of the 'src' directory:
"action_input": {
  "path": "src",
  "recursive": false
}

For a recursive listing of the current directory ('.'):
"action_input": {
  "path": ".",
  "recursive": true
}

## Tool Output Format (Observation):
The tool will return a JSON string as its observation. This JSON object will have the following keys:
- 'path': (string) The input path that was listed.
- 'files': (list of strings, optional) A list of file and directory names found. Directories will have a '/' suffix.
           This list will be empty if no items are found. Present if no error.
- 'error': (string, optional) An error message if something went wrong during the listing.
           If present, the 'files' key might be absent or its list empty.

## Example Tool Outputs (Observation JSON):

Example 1: Successful non-recursive listing of current directory:
{
  "path": ".",
  "files": [
    "src/",
    "installme.md",
    "pyproject.toml"
  ]
}

Example 2: Path not found:
{
  "path": "non_existent_path/",
  "error": "Path does not exist: non_existent_path/"
}

Example 3: Empty directory:
{
  "path": "empty_dir/",
  "files": []
}
""")
