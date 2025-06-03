# Prompt for attempt_completion tool

from textwrap import dedent

ATTEMPT_COMPLETION_PROMPT = dedent("""
# attempt_completion Tool

Description: Present the task result to the user. Optionally provide a CLI command to demo the result.
IMPORTANT NOTE: This tool CANNOT be used until you've confirmed from the user that any previous tool uses were successful. Failure to do so will result in code corruption and system failure. Before using this tool, you must ask yourself in <thinking></thinking> tags if you've confirmed from the user that any previous tool uses were successful. If not, then DO NOT use this tool.

## Parameters for 'action_input' object:
- result: (string, required) The final message to the user, summarizing the successful completion of the task. This message should be conclusive and not ask for further interaction or offer more help on the current task.

## Example of how to structure your JSON response to use this tool:
If your thought process determines the task is complete and you want to inform the user:

Your JSON response would be:
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
""")
