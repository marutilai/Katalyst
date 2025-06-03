# Prompt for attempt_completion tool

from textwrap import dedent

ATTEMPT_COMPLETION_PROMPT = dedent("""
# attempt_completion Tool

Description: Present the final result of the task to the user. Only use this tool after confirming all previous tool uses were successful. This message should be conclusive and not ask for further interaction or offer more help on the current task.

## Parameters for 'action_input' object:
- result: (string, required) The final message to the user, summarizing the successful completion of the task.

## Example of how to structure your JSON response to use this tool:
If your thought process determines the task is complete and you want to inform the user:

{
  "thought": "The user requested to create a new directory called 'project_docs' and it has been successfully created. The sub-task to inform them of the completion is next. I will use attempt_completion for this.",
  "action": "attempt_completion",
  "action_input": {
    "result": "I have successfully created the 'project_docs' directory. You can now use it to store your documentation files. This task is now complete."
  }
}

Another example, if a file was created:
{
  "thought": "The Python script 'hello.py' has been successfully written and saved. The main task is complete.",
  "action": "attempt_completion",
  "action_input": {
    "result": "The Python script 'hello.py' has been created. You can run it using 'python hello.py'."
  }
}

## Tool Output Format (Observation):
The tool will return a JSON string as its observation. This JSON object will have the following keys:
- 'success': (boolean) True if the result was presented successfully, False otherwise.
- 'result': (string, optional) The result message presented to the user (if successful).
- 'error': (string, optional) An error message if something went wrong (e.g., no result provided).

## Example Tool Outputs (Observation JSON):

Example 1: Successful completion message:
{
  "success": true,
  "result": "I have successfully created the 'project_docs' directory. You can now use it to store your documentation files. This task is now complete."
}

Example 2: Error (no result provided):
{
  "success": false,
  "error": "No result provided."
}
""")
