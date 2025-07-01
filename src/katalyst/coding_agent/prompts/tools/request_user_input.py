from textwrap import dedent

REQUEST_USER_INPUT_TOOL_PROMPT = dedent("""
# request_user_input Tool

Description: Request input from the user when clarification is needed.

Parameters:
- prompt: (string, required) Question or message for the user
- context: (string, optional) Additional context about why input is needed

Output: JSON with keys: 'user_input', 'error'
""")