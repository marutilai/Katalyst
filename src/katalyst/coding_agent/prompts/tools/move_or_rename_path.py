from textwrap import dedent

MOVE_OR_RENAME_PATH_PROMPT = dedent("""
# move_or_rename_path Tool

Description: Moves or renames a file or directory. It automatically
sanitizes filenames (e.g., replaces spaces with underscores) and preserves
file extensions unless a new one is provided.

- To rename, `destination_path` is the new name.
- To move, `destination_path` is the target directory.

## Parameters:
- source_path: (string, required) The path of the file/directory to move or rename.
- destination_path: (string, required) The destination path or new name.

## Example:
{
  "thought": "I need to rename the file 'old_name.txt' to 'new_name.txt'. I will use the move_or_rename_path tool for this.",
  "action": "move_or_rename_path",
  "action_input": {
    "source_path": "old_name.txt",
    "destination_path": "new_name.txt"
  }
}

## Output Format:
JSON with keys: 'success' (boolean), 'source_path', 'destination_path', 'info' (optional), 'error' (optional)

Example outputs:
- Success: {"success": true, "source_path": "old.txt", "destination_path": "new.txt", "info": "Successfully moved 'old.txt' to 'new.txt'"}
- Error: {"success": false, "source_path": "fake.txt", "destination_path": "real.txt", "error": "Source path does not exist: fake.txt"}
""")
