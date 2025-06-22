# Prompt for attempt_completion tool

from textwrap import dedent

ATTEMPT_COMPLETION_PROMPT = dedent("""
# attempt_completion Tool

Description: Present the final result of the task to the user. Only use after confirming all previous tool uses were successful. Message should be conclusive, not asking for further interaction.

## Parameters:
- result: (string, required) Final message summarizing successful task completion

## Example:
{
  "thought": "The directory 'project_docs' has been successfully created. I will inform the user of completion.",
  "action": "attempt_completion",
  "action_input": {
    "result": "I have successfully created the 'project_docs' directory. You can now use it to store your documentation files."
  }
}

## Output Format:
JSON with keys: 'success' (boolean), 'result' (optional), 'error' (optional)

Example outputs:
- Success: {"success": true, "result": "Task completed successfully"}
- Error: {"success": false, "error": "No result provided"}
""")
