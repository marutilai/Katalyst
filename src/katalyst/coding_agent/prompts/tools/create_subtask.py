from textwrap import dedent

CREATE_SUBTASK_TOOL_PROMPT = dedent("""
# create_subtask Tool

Description: Decompose the current task into smaller subtasks when complexity is discovered.

Parameters:
- subtasks: (array, required) List of subtask descriptions

Output: JSON with keys: 'success', 'subtasks', 'error'
""")