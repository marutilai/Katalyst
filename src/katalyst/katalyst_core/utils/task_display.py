"""
Task Display Utilities

Provides utilities for displaying task hierarchies and progress in a clear,
hierarchical format for both agent context and user display.
"""

from typing import List, Tuple, Set, Dict
from katalyst.katalyst_core.state import KatalystState


def build_task_hierarchy(state: KatalystState, include_progress: bool = True) -> List[str]:
    """
    Build a hierarchical view of all tasks showing parent-child relationships.
    
    Args:
        state: The current Katalyst state
        include_progress: Whether to include checkmarks for completed tasks
        
    Returns:
        List of formatted task lines
    """
    lines = []
    completed_task_names = {task[0] for task in state.completed_tasks} if include_progress else set()
    
    # Build complete task list: original plan + any new tasks from replanner
    all_tasks = []
    
    # Start with original plan if available
    if state.original_plan:
        all_tasks.extend(state.original_plan)
    
    # Add any tasks from current queue that aren't in original plan
    for task in state.task_queue:
        if task not in all_tasks:
            all_tasks.append(task)
    
    # Also include completed tasks that might not be in either list
    for task_name, _ in state.completed_tasks:
        if task_name not in all_tasks:
            all_tasks.append(task_name)
    
    # Process each task
    for task_idx, task in enumerate(all_tasks):
        task_num = task_idx + 1
        
        # Check if task is completed
        is_completed = task in completed_task_names
        marker = "✓" if is_completed and include_progress else " "
        lines.append(f"{marker} {task_num}. {task}")
        
        # MINIMAL: created_subtasks is commented out
        # # Add any dynamically created subtasks for this parent
        # if state.created_subtasks and parent_idx in state.created_subtasks:
        #     subtasks = state.created_subtasks[parent_idx]
        #     for sub_idx, subtask in enumerate(subtasks):
        #         sub_letter = chr(ord('a') + sub_idx)  # a, b, c, ...
        #         sub_is_completed = subtask in completed_task_names
        #         sub_marker = "✓" if sub_is_completed and include_progress else " "
        #         lines.append(f"     {sub_marker} {parent_num}.{sub_letter}. {subtask}")
    
    return lines


def get_task_progress_display(state: KatalystState) -> str:
    """
    Generate a complete task progress display with header and formatting.
    
    Args:
        state: The current Katalyst state
        
    Returns:
        Formatted progress display string
    """
    # Count totals based on all tasks (original + replanned)
    # This ensures accurate count when replanner adds new tasks
    all_task_count = len(set(
        list(state.original_plan or []) + 
        list(state.task_queue) + 
        [task[0] for task in state.completed_tasks]
    ))
    total_tasks = all_task_count
    completed_count = len(state.completed_tasks)
    
    # Build display
    lines = [
        f"\n{'='*60}",
        f"=== Task Progress ({completed_count}/{total_tasks} completed) ===",
        f"{'='*60}"
    ]
    
    # Add hierarchical task list
    lines.extend(build_task_hierarchy(state, include_progress=True))
    
    lines.append(f"{'='*60}\n")
    
    return "\n".join(lines)


