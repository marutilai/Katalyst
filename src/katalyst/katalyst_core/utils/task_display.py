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
    
    # If no original plan, use current task queue
    plan_tasks = state.original_plan or state.task_queue
    
    # Process each parent task
    for parent_idx, parent_task in enumerate(plan_tasks):
        parent_num = parent_idx + 1
        
        # Check if parent task is completed
        is_completed = parent_task in completed_task_names
        marker = "✓" if is_completed and include_progress else " "
        lines.append(f"{marker} {parent_num}. {parent_task}")
        
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
    # Count totals
    total_tasks = len(state.task_queue)
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


