from textwrap import dedent

REQUEST_USER_INPUT_PROMPT = dedent("""
# request_user_input Tool

Use this tool WHENEVER you need ANY information, clarification, confirmation, choice, filename, content, or other input FROM THE HUMAN USER. Do NOT output questions as 'final_answer'.

## Parameters:
- question_to_ask_user: (string, required) Clear, specific question
- suggested_responses: (list of strings, required) 2-4 actionable, complete suggestions

## Example:
{
  "thought": "I need a filename from the user. I'll ask with common Python script names as suggestions.",
  "action": "request_user_input",
  "action_input": {
    "question_to_ask_user": "What filename for the new Python script?",
    "suggested_responses": ["main.py", "app.py", "utils.py", "script.py"]
  }
}

## Output Format:
JSON with keys: 'question_to_ask_user', 'user_final_answer'
- user_final_answer: Selected suggestion or custom response
- Special case: '[USER_NO_ANSWER_PROVIDED]' if interaction failed
""")
