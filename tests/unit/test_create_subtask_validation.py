import pytest
from katalyst.coding_agent.tools.create_subtask import create_subtask
import json


class TestCreateSubtaskValidation:
    """Test the validation logic in create_subtask tool."""
    
    def test_rejects_file_operation_tasks(self):
        """Test that file-operation-focused tasks are rejected."""
        file_operation_tasks = [
            "Create models directory",
            "Create the models directory with an empty __init__.py file inside 'mytodo'.",
            "Write __init__.py file",
            "Create routers folder",
            "Add imports to main.py",
            "Create empty test.py file",
            "Make a new folder called utils",
        ]
        
        for task in file_operation_tasks:
            result = create_subtask(
                task_description=task,
                reason="Testing file operation rejection"
            )
            response = json.loads(result)
            assert not response["success"], f"Task should be rejected: {task}"
            assert "file-operation" in response["error"].lower(), f"Error should mention file operations: {task}"
    
    def test_accepts_goal_oriented_tasks(self):
        """Test that proper goal-oriented tasks are accepted."""
        good_tasks = [
            "Implement User model with authentication fields",
            "Create Todo CRUD endpoints with validation",
            "Set up database connection and migrations",
            "Add JWT authentication to API endpoints",
            "Implement data validation for Todo model",
        ]
        
        for task in good_tasks:
            result = create_subtask(
                task_description=task,
                reason="Testing good task acceptance"
            )
            response = json.loads(result)
            assert response["success"], f"Task should be accepted: {task}"
            assert response["tasks_created"] == 1
    
    def test_rejects_meta_tasks(self):
        """Test that meta-tasks are still rejected."""
        meta_tasks = [
            "Break down the authentication system",
            "Plan the database structure",
            "Organize the API endpoints",
            "Create subtasks for building the app",
        ]
        
        for task in meta_tasks:
            result = create_subtask(
                task_description=task,
                reason="Testing meta task rejection"
            )
            response = json.loads(result)
            assert not response["success"], f"Meta task should be rejected: {task}"
            assert "meta-task" in response["error"].lower()
    
    def test_edge_cases(self):
        """Test edge cases for task validation."""
        # Task that mentions directory but in a higher-level context
        result = create_subtask(
            task_description="Set up project structure with models, routers, and services directories",
            reason="Testing edge case"
        )
        response = json.loads(result)
        # This should be accepted as it's about project structure, not just creating a directory
        assert response["success"], "Project structure setup should be accepted"
        
        # Task that's about implementing something in a directory
        result = create_subtask(
            task_description="Implement all database models in the models directory",
            reason="Testing edge case"
        )
        response = json.loads(result)
        assert response["success"], "Implementation task should be accepted"