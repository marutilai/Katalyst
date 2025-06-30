"""
Tests for task utility functions.
"""
import pytest
from katalyst.katalyst_core.utils.task_utils import find_parent_planner_task_index


class TestFindParentPlannerTaskIndex:
    """Test the find_parent_planner_task_index function."""
    
    def test_task_from_original_plan(self):
        """Test finding parent for a task that's in the original plan."""
        original_plan = ["Task A", "Task B", "Task C"]
        created_subtasks = {}
        
        # Task B is at index 1 in original plan
        result = find_parent_planner_task_index(
            "Task B", 
            1, 
            original_plan, 
            created_subtasks
        )
        assert result == 1
    
    def test_dynamically_created_subtask(self):
        """Test finding parent for a dynamically created subtask."""
        original_plan = ["Task A", "Task B", "Task C"]
        created_subtasks = {
            0: ["Subtask A1", "Subtask A2"],
            1: ["Subtask B1", "Subtask B2"]
        }
        
        # Subtask B2 belongs to parent at index 1
        result = find_parent_planner_task_index(
            "Subtask B2",
            4,  # Some index in the queue
            original_plan,
            created_subtasks
        )
        assert result == 1
    
    def test_task_not_found(self):
        """Test when task is not found in either original plan or subtasks."""
        original_plan = ["Task A", "Task B"]
        created_subtasks = {0: ["Subtask A1"]}
        
        result = find_parent_planner_task_index(
            "Unknown Task",
            2,
            original_plan,
            created_subtasks
        )
        assert result is None
    
    def test_no_original_plan(self):
        """Test when there's no original plan."""
        result = find_parent_planner_task_index(
            "Some Task",
            0,
            None,
            {}
        )
        assert result is None
    
    def test_empty_created_subtasks(self):
        """Test with empty created_subtasks dict."""
        original_plan = ["Task A", "Task B"]
        
        # Task not in original plan and no subtasks created
        result = find_parent_planner_task_index(
            "Task C",
            2,
            original_plan,
            {}
        )
        assert result is None