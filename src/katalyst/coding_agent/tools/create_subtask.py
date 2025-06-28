import json
from typing import Optional
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import katalyst_tool


def format_create_subtask_response(
    success: bool, 
    message: str,
    tasks_created: int = 0,
    error: Optional[str] = None
) -> str:
    """Format the response for create_subtask tool."""
    resp = {
        "success": success,
        "message": message,
        "tasks_created": tasks_created
    }
    if error:
        resp["error"] = error
    return json.dumps(resp)


@katalyst_tool(prompt_module="create_subtask", prompt_var="CREATE_SUBTASK_PROMPT")
def create_subtask(
    task_description: str,
    reason: str,
    insert_position: str = "after_current"
) -> str:
    """
    Creates a new subtask and adds it to the task queue.
    This tool is handled specially by the tool_runner to modify the agent's state.
    
    Arguments:
        task_description: Clear description of the subtask to create
        reason: Why this subtask is needed (helps with debugging)
        insert_position: Where to insert ("after_current" or "end_of_queue")
    
    Returns:
        JSON string with success status and message
    """
    logger = get_logger()
    
    # Validate inputs
    if not task_description or not isinstance(task_description, str):
        return format_create_subtask_response(
            False, 
            "Task description is required",
            error="Invalid task_description"
        )
    
    if not reason or not isinstance(reason, str):
        return format_create_subtask_response(
            False,
            "Reason for creating subtask is required", 
            error="Invalid reason"
        )
    
    if insert_position not in ["after_current", "end_of_queue"]:
        return format_create_subtask_response(
            False,
            "Insert position must be 'after_current' or 'end_of_queue'",
            error="Invalid insert_position"
        )
    
    # Log the request (actual insertion happens in tool_runner)
    logger.info(f"[CREATE_SUBTASK] Request to create subtask: '{task_description}' (Reason: {reason})")
    
    # Return success - the tool_runner will handle the actual state modification
    return format_create_subtask_response(
        True,
        f"Subtask creation request processed. Task: '{task_description}'",
        tasks_created=1
    )