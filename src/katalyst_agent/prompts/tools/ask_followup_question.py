from textwrap import dedent

ASK_FOLLOWUP_QUESTION_PROMPT = dedent("""
# ask_followup_question Tool

Use this tool to ask the user a clear, specific question when you need more information to proceed. Provide 2-4 suggested answers, each in its own <suggest> tag, that are actionable and complete (no placeholders).

Parameters:
- question: (required) The question to ask the user.
- follow_up: (required) 2-4 suggested answers, each in a <suggest> tag.

## Usage
<ask_followup_question>
<question>Your question here</question>
<follow_up>
<suggest>Your suggested answer here</suggest>
<suggest>Another suggestion</suggest>
</follow_up>
</ask_followup_question>

## Example
<ask_followup_question>
<question>What is the path to the frontend-config.json file?</question>
<follow_up>
<suggest>./src/frontend-config.json</suggest>
<suggest>./config/frontend-config.json</suggest>
<suggest>./frontend-config.json</suggest>
</follow_up>
</ask_followup_question>
""") 