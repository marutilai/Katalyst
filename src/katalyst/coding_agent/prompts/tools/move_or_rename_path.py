MOVE_OR_RENAME_PATH_PROMPT = """
- tool: move_or_rename_path
  description: Moves or renames a file or directory.
    - To rename, `destination_path` is the new name.
    - To move, `destination_path` is the target directory.
  args:
    - name: source_path
      type: string
      description: The path of the file/directory to move or rename.
    - name: destination_path
      type: string
      description: The destination path or new name.
  response:
    - name: source_path
      type: string
      description: Original source path.
    - name: destination_path
      type: string
      description: Final destination path.
    - name: success
      type: boolean
      description: True if successful.
    - name: info
      type: string
      description: Success message.
    - name: error
      type: string
      description: Error message on failure.
  examples:
    - To rename a file:
      - thoughts: Rename 'old.txt' to 'new.txt'.
      - tool_code: print(move_or_rename_path(source_path='old.txt', destination_path='new.txt'))
      - tool_output: '{"source_path": "old.txt", "destination_path": "new.txt", "success": true, "info": "Successfully moved \'old.txt\' to \'new.txt\'"}'
    - To move a file:
      - thoughts: Move 'main.py' into the 'app/' directory.
      - tool_code: print(move_or_rename_path(source_path='main.py', destination_path='app/'))
      - tool_output: '{"source_path": "main.py", "destination_path": "app/main.py", "success": true, "info": "Successfully moved \'main.py\' to \'app/\'"}'
    - Error on non-existent source:
      - thoughts: Attempt to move a file that does not exist.
      - tool_code: print(move_or_rename_path(source_path='fake.txt', destination_path='real.txt'))
      - tool_output: '{"source_path": "fake.txt", "destination_path": "real.txt", "success": false, "error": "Source path does not exist: fake.txt"}'
"""
