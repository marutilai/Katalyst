# katalyst_agent/prompts/tools/ask_followup_question.py
from textwrap import dedent

ASK_FOLLOWUP_QUESTION_PROMPT = dedent("""
# ask_followup_question Tool

Description: Use this tool to ask the user a question when you need more information, clarification, or further details to proceed effectively. This enables interactive problem-solving. Provide 2-4 actionable suggested answers. The user can select a suggestion or provide a custom answer. Use judiciously to avoid excessive back-and-forth.

## Parameters for 'action_input' object:
- question: (string, required) The clear, specific question to ask the user.
- follow_up: (list of strings, required) A JSON list containing 2-4 suggested answers. Each suggestion string must be:
    1. Actionable and directly related to the task or question.
    2. A complete answer (no placeholders like "[fill this in]").
    3. Logically ordered if applicable.

## Usage Example (how to structure 'action_input' in your JSON response):
If you need to ask the user for clarification, the 'action_input' in your main JSON response
for the ReAct step should be an object structured like this:

"action_input": {
  "question": "What is the name of the main Python file for the Flask application?",
  "follow_up": [
    "app.py",
    "main.py",
    "server.py"
  ]
}

## Tool Output Format (Observation):
The tool will return a JSON string as its observation. This JSON object will have the following keys:
- 'question': (string) The original question that was asked.
- 'answer': (string) The answer provided by the user (either one of the suggestions or a custom response).
            This may also indicate an error if no valid answer was provided (e.g., "[USER_NO_ANSWER_PROVIDED]").

## Example Tool Outputs (Observation JSON):

Example 1: User selects a suggestion:
{
  "question": "What is the path to the frontend-config.json file?",
  "answer": "./src/frontend-config.json"
}

Example 2: User provides a custom answer:
{
  "question": "What framework should I use for the UI?",
  "answer": "Let's use Material UI with React."
}

Example 3: User provides no answer (or an invalid choice leads to no answer):
{
  "question": "What is your favorite color?",
  "answer": "[USER_NO_ANSWER_PROVIDED]" 
}
""")