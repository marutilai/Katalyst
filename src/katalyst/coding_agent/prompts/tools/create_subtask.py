from textwrap import dedent

CREATE_SUBTASK_TOOL_PROMPT = dedent("""
# create_subtask Tool

Description: Create a new subtask when discovering complexity during task execution.

Parameters:
- task_description: (string, required) Clear description of the subtask
- reason: (string, required) Why this subtask is needed
- insert_position: (string, optional) "after_current" or "end_of_queue"

Output: JSON with keys: 'success', 'message', 'tasks_created', 'error'
""")