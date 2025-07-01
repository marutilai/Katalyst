import json
import re
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


@katalyst_tool(prompt_module="create_subtask", prompt_var="CREATE_SUBTASK_TOOL_PROMPT")
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
    
    # Check for meta-tasks (tasks that just decompose further)
    task_lower = task_description.lower()
    meta_patterns = [
        "break down",
        "decompose",
        "create subtasks",
        "plan the",
        "organize the",
        "structure the",
        "divide into",
        "split into",
        "analyze and create",
        "identify and implement",
        "create tasks for",
        "create all",
        "plan out"
    ]
    
    if any(pattern in task_lower for pattern in meta_patterns):
        logger.warning(f"[CREATE_SUBTASK] Rejected meta-task: '{task_description}'")
        return format_create_subtask_response(
            False,
            "Task appears to be a meta-task that would require further decomposition. Please create concrete, actionable tasks instead.",
            error="Meta-task detected - create concrete tasks instead"
        )
    
    # Check for overly vague tasks
    vague_patterns = [
        "handle",
        "process",
        "deal with",
        "work on",
        "take care of"
    ]
    
    # Only flag as vague if it's very short AND contains vague patterns
    if len(task_description.split()) <= 4 and any(pattern in task_lower for pattern in vague_patterns):
        logger.warning(f"[CREATE_SUBTASK] Rejected vague task: '{task_description}'")
        return format_create_subtask_response(
            False,
            "Task description is too vague. Please be specific about what needs to be done.",
            error="Task too vague - be more specific"
        )
    
    # Check for file-operation-focused tasks
    file_operation_patterns = [
        r"^create .* (directory|folder|dir)$",
        r"^create .* __init__\.py",
        r"^write .* file$",
        r"^add .* import",
        r"^create the .* directory",
        r"^make .* folder",
        r"^write __init__\.py",
        r"^create empty .* file",
        r"^add .* to .*\.py$"
    ]
    
    for pattern in file_operation_patterns:
        if re.search(pattern, task_lower):
            logger.warning(f"[CREATE_SUBTASK] Rejected file-operation task: '{task_description}'")
            return format_create_subtask_response(
                False,
                "Task is too focused on file operations. Tasks should represent meaningful work units (e.g., 'Implement User model' not 'Create user.py file'). File operations are implementation details, not tasks.",
                error="File-operation task - think higher level"
            )
    
    # Log the request (actual insertion happens in tool_runner)
    logger.info(f"[CREATE_SUBTASK] Request to create subtask: '{task_description}' (Reason: {reason})")
    
    # Return success - the tool_runner will handle the actual state modification
    return format_create_subtask_response(
        True,
        f"Subtask creation request processed. Task: '{task_description}'",
        tasks_created=1
    )