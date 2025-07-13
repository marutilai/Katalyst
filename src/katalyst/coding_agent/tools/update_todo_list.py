import json
from typing import List, Optional, Literal
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import katalyst_tool
from katalyst.katalyst_core.utils.todo_manager import todo_aware


def format_update_response(
    success: bool,
    message: str,
    updated_list: Optional[List[str]] = None,
    error: Optional[str] = None
) -> str:
    """Format the response for update_todo_list tool."""
    resp = {
        "success": success,
        "message": message,
    }
    if updated_list is not None:
        resp["updated_list"] = updated_list
        resp["task_count"] = len(updated_list)
    if error:
        resp["error"] = error
    return json.dumps(resp, indent=2)


@katalyst_tool(prompt_module="update_todo_list", prompt_var="UPDATE_TODO_LIST_TOOL_PROMPT")
@todo_aware(action="update")
def update_todo_list(
    action: Literal["add", "remove", "complete", "reorder", "show"],
    task_description: Optional[str] = None,
    task_index: Optional[int] = None,
    new_position: Optional[int] = None,
    reason: Optional[str] = None
) -> str:
    """
    Updates the current todo list by adding, removing, completing, reordering tasks, or showing the current list.
    This tool is handled specially by the tool_runner to modify the agent's state.
    
    Arguments:
        action: The action to perform ("add", "remove", "complete", "reorder", "show")
        task_description: Description of the task (required for "add" action)
        task_index: Index of the task (1-based, required for "remove", "complete", "reorder")
        new_position: New position for reordering (1-based, required for "reorder")
        reason: Explanation for the change (optional but recommended)
    
    Returns:
        JSON string with the updated todo list and status
    """
    logger = get_logger()
    logger.debug(f"[TOOL] Updating todo list with action='{action}'")
    
    # Validate action
    valid_actions = ["add", "remove", "complete", "reorder", "show"]
    if action not in valid_actions:
        return format_update_response(
            False,
            f"Invalid action. Must be one of: {', '.join(valid_actions)}",
            error="Invalid action"
        )
    
    # Action-specific validation
    if action == "add":
        if not task_description or not isinstance(task_description, str):
            return format_update_response(
                False,
                "Task description is required for 'add' action",
                error="Missing task_description"
            )
        
        # Check for meta-tasks (similar to create_subtask validation)
        task_lower = task_description.lower()
        meta_patterns = [
            "break down", "decompose", "create subtasks", "plan the",
            "organize the", "structure the", "divide into", "split into"
        ]
        
        if any(pattern in task_lower for pattern in meta_patterns):
            logger.warning(f"[UPDATE_TODO_LIST] Rejected meta-task: '{task_description}'")
            return format_update_response(
                False,
                "Task appears to be a meta-task. Please add concrete, actionable tasks instead.",
                error="Meta-task detected"
            )
    
    elif action in ["remove", "complete", "reorder"]:
        if task_index is None or not isinstance(task_index, int) or task_index < 1:
            return format_update_response(
                False,
                f"Valid task index (1-based) is required for '{action}' action",
                error="Invalid task_index"
            )
    
    if action == "reorder":
        if new_position is None or not isinstance(new_position, int) or new_position < 1:
            return format_update_response(
                False,
                "Valid new position (1-based) is required for 'reorder' action",
                error="Invalid new_position"
            )
    
    # Log the request (actual modification happens in tool_runner)
    log_message = f"[UPDATE_TODO_LIST] Request to {action}"
    if task_description:
        log_message += f" task: '{task_description}'"
    if task_index:
        log_message += f" at index {task_index}"
    if new_position:
        log_message += f" to position {new_position}"
    if reason:
        log_message += f" (Reason: {reason})"
    
    logger.info(log_message)
    
    # Return success - the tool_runner will handle the actual state modification
    # and populate the updated_list
    return format_update_response(
        True,
        f"Todo list update request processed: {action}",
        updated_list=None  # Will be populated by tool_runner
    )