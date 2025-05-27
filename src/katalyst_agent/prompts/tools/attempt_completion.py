# Prompt for attempt_completion tool

from textwrap import dedent

ATTEMPT_COMPLETION_PROMPT = dedent("""
# attempt_completion Tool

Use this tool to present the final result of the task to the user. Only use this after confirming all previous tool uses were successful. Do not end with questions or offers for further help.

Parameters:
- result: (required) The final result description. This should be complete and not require further user input.

## Usage
<attempt_completion>
<result>
Your final result description here
</result>
</attempt_completion>

## Example
<attempt_completion>
<result>
I've updated the CSS, run `open index.html` to see the changes.
</result>
</attempt_completion>
""")
