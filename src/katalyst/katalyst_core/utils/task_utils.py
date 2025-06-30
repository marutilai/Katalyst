"""
Task-related utility functions.

Provides common utilities for working with tasks, including finding parent planner tasks.
"""
from typing import Optional, Dict, List


def find_parent_planner_task_index(
    current_task: str,
    current_task_idx: int,
    original_plan: Optional[List[str]],
    created_subtasks: Dict[int, List[str]]
) -> Optional[int]:
    """
    Find the parent planner task index for a given task.
    
    This is used when creating subtasks to properly track which planner task
    they belong to.
    
    Args:
        current_task: The current task description
        current_task_idx: The current task index in the queue
        original_plan: The original plan from the planner
        created_subtasks: Dictionary mapping planner task indices to their created subtasks
        
    Returns:
        The parent planner task index, or None if not found
    """
    if not original_plan:
        return None
        
    # Check if current task is from original plan
    if current_task in original_plan:
        return original_plan.index(current_task)
    
    # It's a dynamically created subtask - find its parent
    for planner_idx, subtasks in created_subtasks.items():
        if current_task in subtasks:
            return planner_idx
    
    # Couldn't find parent
    return None