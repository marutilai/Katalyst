from textwrap import dedent

REQUEST_USER_INPUT_PROMPT = dedent("""
# request_user_input Tool

Description: Use this tool WHENEVER you need ANY information, clarification, confirmation, choice, filename, content, or other input FROM THE HUMAN USER. Do NOT output questions as 'final_answer'.

## When to Use:
- Getting user preferences or choices
- Requesting file/directory names
- Asking for confirmation before major changes
- Clarifying ambiguous requirements
- Getting API keys, URLs, or configuration values
- When task description is unclear

## Parameters:
- question_to_ask_user: (string, required) Clear, specific question
- suggested_responses: (list of strings, required) 2-4 actionable, complete suggestions

## Example:
{
  "thought": "I need a filename from the user for the new file.",
  "action": "request_user_input",
  "action_input": {
    "question_to_ask_user": "What should I name this file?",
    "suggested_responses": ["file1.py", "file2.py", "module.py", "handler.py"]
  }
}

## Output Format:
JSON with keys: 'question_to_ask_user', 'user_final_answer'
- user_final_answer: Selected suggestion or custom response
- Special case: '[USER_NO_ANSWER_PROVIDED]' if interaction failed
""")
