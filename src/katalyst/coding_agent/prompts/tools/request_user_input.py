from textwrap import dedent

REQUEST_USER_INPUT_TOOL_PROMPT = dedent("""
# request_user_input Tool

Description: Ask the user a question and provide suggested answer options for them to choose from.

Parameters:
- question_to_ask_user: (string, required) The question to ask the user
- suggested_responses: (list of strings, required) List of suggested answer options. Must be non-empty.

Output: JSON with keys: 'question_to_ask_user', 'user_final_answer'

Example usage:
```
request_user_input(
    question_to_ask_user="Which framework would you like to use for the backend?",
    suggested_responses=["FastAPI", "Django", "Flask", "Other (I'll specify)"]
)
```

Important: You MUST always provide suggested_responses. The tool will return an error if this parameter is missing or empty.
""")