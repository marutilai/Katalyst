import pytest
import json
from katalyst.coding_agent.tools.create_subtask import create_subtask, format_create_subtask_response

class TestCreateSubtask:
    """Test the create_subtask tool functionality."""
    
    def test_create_subtask_success(self):
        """Test successful subtask creation."""
        result = create_subtask(
            task_description="Implement User model with authentication",
            reason="User model is complex and needs focused implementation",
            insert_position="after_current"
        )
        
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert "Subtask creation request processed" in result_data["message"]
        assert result_data["tasks_created"] == 1
    
    def test_create_subtask_missing_description(self):
        """Test error when task description is missing."""
        result = create_subtask(
            task_description="",
            reason="Some reason",
            insert_position="after_current"
        )
        
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "Task description is required" in result_data["message"]
        assert result_data["error"] == "Invalid task_description"
    
    def test_create_subtask_missing_reason(self):
        """Test error when reason is missing."""
        result = create_subtask(
            task_description="Some task",
            reason="",
            insert_position="after_current"
        )
        
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "Reason for creating subtask is required" in result_data["message"]
        assert result_data["error"] == "Invalid reason"
    
    def test_create_subtask_invalid_position(self):
        """Test error when insert position is invalid."""
        result = create_subtask(
            task_description="Some task",
            reason="Some reason",
            insert_position="invalid_position"
        )
        
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "Insert position must be" in result_data["message"]
        assert result_data["error"] == "Invalid insert_position"
    
    def test_create_subtask_end_of_queue(self):
        """Test subtask creation with end_of_queue position."""
        result = create_subtask(
            task_description="Add comprehensive tests",
            reason="Tests should be added after all implementation is done",
            insert_position="end_of_queue"
        )
        
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert result_data["tasks_created"] == 1
    
    def test_format_response_with_error(self):
        """Test response formatting with error."""
        result = format_create_subtask_response(
            success=False,
            message="Something went wrong",
            tasks_created=0,
            error="Test error"
        )
        
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert result_data["message"] == "Something went wrong"
        assert result_data["tasks_created"] == 0
        assert result_data["error"] == "Test error"