from textwrap import dedent

ATTEMPT_COMPLETION_TOOL_PROMPT = dedent("""
# attempt_completion Tool

Description: Presents the final result of the task to the user. Only use this after confirming all previous tool uses were successful.

Parameters:
- result: (string, required) The final result description/summary of what was accomplished

Output: JSON with keys: 'success', 'result' (optional), 'error' (optional)
""")