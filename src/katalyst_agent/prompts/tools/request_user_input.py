from textwrap import dedent

REQUEST_USER_INPUT_PROMPT = dedent("""
# request_user_input Tool

## Description (for LLM):
Use this tool WHENEVER the current sub-task requires you to obtain ANY information, clarification, confirmation, a choice, a filename, content for a file, or any other input FROM THE HUMAN USER.
You MUST use this tool for all direct user queries; do NOT attempt to formulate the question yourself and output it as a 'final_answer' for the sub-task.

Your role when using this tool is to:
1. Formulate the specific `question_to_ask_user`.
2. Generate 2–4 concise, actionable, and complete `suggested_responses` that the user can choose from.

The tool will then present your question and suggestions to the user and return their chosen answer or custom input.

## Parameters for YOUR 'action_input' object (the JSON object you provide when calling this tool):
- question_to_ask_user: (string, required) The clear, specific question you have formulated to ask the user.
- suggested_responses: (list of strings, required) A JSON list containing 2 to 4 distinct suggestion strings that you generate. Each suggestion must be:
  1. Actionable and directly relevant to your `question_to_ask_user`.
  2. A complete potential answer (no placeholders like "[fill this in]").
  3. Logically ordered if applicable.

## Example of how to structure YOUR JSON response to use this tool:
If your thought process determines you need to ask the user for a filename:
{
  "thought": "The sub-task is to get a filename from the user. I must use the 'request_user_input' tool. I will formulate a clear question and provide some common Python script names as suggestions.",
  "action": "request_user_input",
  "action_input": {
    "question_to_ask_user": "What filename would you like to use for the new Python script?",
    "suggested_responses": ["main.py", "app.py", "utils.py", "script.py"]
  }
}

Another example, asking for confirmation with generated suggestions:
{
  "thought": "I have drafted the content for 'config.json'. I need to ask the user to confirm before writing it. I'll provide 'Yes' and 'No' options as suggestions, and an option to review.",
  "action": "request_user_input",
  "action_input": {
    "question_to_ask_user": "I have drafted the content for 'config.json'. It includes [brief summary of content]. Do you want me to write this to the file?",
    "suggested_responses": [
      "Yes, write the drafted content to 'config.json'.",
      "No, let me review or change the content first.",
      "No, cancel writing 'config.json' for now."
    ]
  }
}

## Tool Output Format (Observation – what YOU will receive back after this tool runs):
The tool will return a JSON string as its observation. This JSON object will have the following keys:
- 'question_to_ask_user': (string) The original question that was actually presented to the user (from your 'question_to_ask_user' input).
- 'user_final_answer': (string) The answer ultimately provided by the user. This will be one of your 'suggested_responses' if they selected one, or their custom typed response. It might also be a special string like '[USER_NO_ANSWER_PROVIDED]' if the interaction failed.
""") 