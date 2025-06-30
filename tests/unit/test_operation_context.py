"""
Unit tests for OperationContext
"""

import pytest
from katalyst.katalyst_core.utils.operation_context import (
    OperationContext,
    FileOperation,
    ToolOperation,
)


class TestOperationContext:
    """Test the OperationContext functionality."""
    
    def test_add_file_operation(self):
        """Test adding file operations."""
        context = OperationContext(file_history_limit=5)
        
        # Add file operations
        context.add_file_operation("/path/to/file1.py", "created")
        context.add_file_operation("/path/to/file2.py", "modified")
        context.add_file_operation("/path/to/file3.py", "read")
        
        # Check operations were added
        assert len(context.file_operations) == 3
        assert context.file_operations[0].file_path == "/path/to/file1.py"
        assert context.file_operations[0].operation == "created"
        
    def test_file_history_limit(self):
        """Test that file history respects the limit."""
        context = OperationContext(file_history_limit=3)
        
        # Add more operations than the limit
        for i in range(5):
            context.add_file_operation(f"/path/to/file{i}.py", "created")
        
        # Should only keep last 3
        assert len(context.file_operations) == 3
        assert context.file_operations[0].file_path == "/path/to/file2.py"
        assert context.file_operations[-1].file_path == "/path/to/file4.py"
    
    def test_add_tool_operation(self):
        """Test adding tool operations."""
        context = OperationContext(operations_history_limit=5)
        
        # Add tool operations
        context.add_tool_operation(
            tool_name="write_to_file",
            tool_input={"path": "test.py", "content": "print('hello')"},
            success=True,
            summary="Created test.py"
        )
        
        context.add_tool_operation(
            tool_name="read_file",
            tool_input={"path": "config.json"},
            success=False,
            summary="File not found"
        )
        
        # Check operations were added
        assert len(context.tool_operations) == 2
        assert context.tool_operations[0].tool_name == "write_to_file"
        assert context.tool_operations[0].success is True
        assert context.tool_operations[1].success is False
    
    def test_was_file_created(self):
        """Test checking if a file was created."""
        context = OperationContext()
        
        # Add some operations
        context.add_file_operation("/path/to/created.py", "created")
        context.add_file_operation("/path/to/modified.py", "modified")
        context.add_file_operation("/path/to/read.py", "read")
        
        # Check file creation
        assert context.was_file_created("/path/to/created.py") is True
        assert context.was_file_created("/path/to/modified.py") is False
        assert context.was_file_created("/path/to/read.py") is False
        assert context.was_file_created("/path/to/nonexistent.py") is False
    
    def test_get_recent_files(self):
        """Test getting recent files with filtering."""
        context = OperationContext()
        
        # Add various operations
        context.add_file_operation("/path/to/file1.py", "created")
        context.add_file_operation("/path/to/file2.py", "modified")
        context.add_file_operation("/path/to/file3.py", "created")
        context.add_file_operation("/path/to/file4.py", "read")
        
        # Get all files
        all_files = context.get_recent_files()
        assert len(all_files) == 4
        
        # Get only created files
        created_files = context.get_recent_files(operation_type="created")
        assert len(created_files) == 2
        assert "/path/to/file1.py" in created_files
        assert "/path/to/file3.py" in created_files
        
        # Get only modified files
        modified_files = context.get_recent_files(operation_type="modified")
        assert len(modified_files) == 1
        assert "/path/to/file2.py" in modified_files
    
    def test_get_context_for_agent(self):
        """Test formatting context for agent prompt."""
        context = OperationContext()
        
        # Add file operations
        context.add_file_operation("/project/src/main.py", "created", "Entry point")
        context.add_file_operation("/project/src/utils.py", "modified")
        
        # Add tool operations
        context.add_tool_operation(
            tool_name="write_to_file",
            tool_input={"path": "main.py"},
            success=True
        )
        context.add_tool_operation(
            tool_name="read_file",
            tool_input={"path": "config.json"},
            success=False,
            summary="File not found"
        )
        
        # Get formatted context
        formatted = context.get_context_for_agent()
        
        # Check it contains expected sections
        assert "=== Recent File Operations ===" in formatted
        assert "=== Recent Tool Operations ===" in formatted
        assert "created: " in formatted
        assert "modified: " in formatted
        assert "✓ write_to_file" in formatted
        assert "✗ read_file" in formatted
        assert "Entry point" in formatted
        assert "File not found" in formatted
    
    def test_clear(self):
        """Test clearing all operations."""
        context = OperationContext()
        
        # Add operations
        context.add_file_operation("/path/to/file.py", "created")
        context.add_tool_operation("write_to_file", {}, True)
        
        # Clear
        context.clear()
        
        # Check everything is cleared
        assert len(context.file_operations) == 0
        assert len(context.tool_operations) == 0
        assert context.get_context_for_agent() == ""
    
    def test_serialization(self):
        """Test to_dict and from_dict methods."""
        context = OperationContext(file_history_limit=5, operations_history_limit=7)
        
        # Add operations
        context.add_file_operation("/path/to/file.py", "created")
        context.add_tool_operation("write_to_file", {"path": "test.py"}, True)
        
        # Serialize
        data = context.to_dict()
        
        # Check data structure
        assert data["file_history_limit"] == 5
        assert data["operations_history_limit"] == 7
        assert len(data["file_operations"]) == 1
        assert len(data["tool_operations"]) == 1
        
        # Deserialize
        new_context = OperationContext.from_dict(data)
        
        # Check restored correctly
        assert new_context._file_history_limit == 5
        assert new_context._operations_history_limit == 7
        assert len(new_context.file_operations) == 1
        assert len(new_context.tool_operations) == 1
        assert new_context.file_operations[0].file_path == "/path/to/file.py"