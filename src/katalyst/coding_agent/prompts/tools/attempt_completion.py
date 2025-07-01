from textwrap import dedent

ATTEMPT_COMPLETION_TOOL_PROMPT = dedent("""
# attempt_completion Tool

Description: Indicate that the task is complete and ready for review.

Parameters:
- message: (string, required) Summary of what was accomplished

Output: Completion status
""")