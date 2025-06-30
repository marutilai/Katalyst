"""
Tests for deterministic state tracking to prevent redundant operations.
"""
import pytest
import os
from katalyst.katalyst_core.utils.operation_context import OperationContext


class TestHasRecentOperation:
    """Test the has_recent_operation method."""
    
    def test_read_file_redundancy_detection(self):
        """Test that read_file operations are detected as redundant."""
        context = OperationContext()
        
        # Add a successful read operation
        context.add_tool_operation(
            tool_name="read_file",
            tool_input={"path": "test.py"},
            success=True,
            summary="test.py"
        )
        
        # Should detect redundancy for same file
        assert context.has_recent_operation("read_file", {"path": "test.py"}) is True
        
        # Should not detect redundancy for different file
        assert context.has_recent_operation("read_file", {"path": "other.py"}) is False
        
        # Should handle absolute paths
        abs_path = os.path.abspath("test.py")
        assert context.has_recent_operation("read_file", {"path": abs_path}) is True
    
    def test_failed_operations_not_redundant(self):
        """Test that failed operations are not considered redundant."""
        context = OperationContext()
        
        # Add a failed read operation
        context.add_tool_operation(
            tool_name="read_file",
            tool_input={"path": "missing.py"},
            success=False,
            summary="File not found"
        )
        
        # Should NOT detect redundancy for failed operations
        assert context.has_recent_operation("read_file", {"path": "missing.py"}) is False
    
    def test_list_files_redundancy_detection(self):
        """Test that list_files operations are detected as redundant."""
        context = OperationContext()
        
        # Add a successful list operation
        context.add_tool_operation(
            tool_name="list_files",
            tool_input={"path": "./src"},
            success=True,
            summary="Listed 10 files"
        )
        
        # Should detect redundancy for same directory
        assert context.has_recent_operation("list_files", {"path": "./src"}) is True
        
        # Should handle absolute paths
        abs_path = os.path.abspath("./src")
        assert context.has_recent_operation("list_files", {"path": abs_path}) is True
        
        # Should not detect redundancy for different directory
        assert context.has_recent_operation("list_files", {"path": "./tests"}) is False
    
    def test_search_operations_redundancy_detection(self):
        """Test that search operations are detected as redundant."""
        context = OperationContext()
        
        # Add a successful search operation
        context.add_tool_operation(
            tool_name="search_in_file",
            tool_input={"pattern": "def test", "path": "test.py"},
            success=True,
            summary="Found 5 matches"
        )
        
        # Should detect redundancy for same pattern and file
        assert context.has_recent_operation(
            "search_in_file", 
            {"pattern": "def test", "path": "test.py"}
        ) is True
        
        # Should not detect redundancy for different pattern
        assert context.has_recent_operation(
            "search_in_file", 
            {"pattern": "class Test", "path": "test.py"}
        ) is False
        
        # Should not detect redundancy for different file
        assert context.has_recent_operation(
            "search_in_file", 
            {"pattern": "def test", "path": "other.py"}
        ) is False
    
    def test_write_operations_never_redundant(self):
        """Test that write operations are never considered redundant."""
        context = OperationContext()
        
        # Add a write operation
        context.add_tool_operation(
            tool_name="write_to_file",
            tool_input={"path": "test.py", "content": "data"},
            success=True
        )
        
        # Should NOT detect redundancy for write operations
        assert context.has_recent_operation(
            "write_to_file", 
            {"path": "test.py", "content": "data"}
        ) is False
    
    def test_history_limit_respected(self):
        """Test that operations beyond history limit are not considered."""
        # Create context with small history limit
        context = OperationContext(operations_history_limit=2)
        
        # Add 3 operations (oldest will be evicted)
        context.add_tool_operation(
            tool_name="read_file",
            tool_input={"path": "file1.py"},
            success=True
        )
        context.add_tool_operation(
            tool_name="read_file",
            tool_input={"path": "file2.py"},
            success=True
        )
        context.add_tool_operation(
            tool_name="read_file",
            tool_input={"path": "file3.py"},
            success=True
        )
        
        # file1.py should no longer be in history (evicted)
        assert context.has_recent_operation("read_file", {"path": "file1.py"}) is False
        
        # file2.py and file3.py should still be in history
        assert context.has_recent_operation("read_file", {"path": "file2.py"}) is True
        assert context.has_recent_operation("read_file", {"path": "file3.py"}) is True