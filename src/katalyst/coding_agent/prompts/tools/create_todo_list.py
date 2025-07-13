from textwrap import dedent

CREATE_TODO_LIST_TOOL_PROMPT = dedent("""
# create_todo_list Tool

Description: Break down a complex task into a comprehensive todo list of implementation steps.

Parameters:
- task_description: (string, required) The task to plan
- include_verification: (boolean, optional) Whether to verify plan with user

Output: JSON with keys: 'success', 'message', 'todo_list', 'task_count', 'error'

Notes:
- Creates production-ready implementation plans
- Each task is a significant feature or component
- Focuses on complete, working solutions
""")