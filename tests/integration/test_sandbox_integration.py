"""Integration tests for sandbox functionality with tools."""

import os
import json
import pytest
from unittest.mock import MagicMock

from katalyst.katalyst_core.state import KatalystState
from katalyst.coding_agent.tools.read import read
from katalyst.coding_agent.tools.write import write


class TestSandboxIntegration:
    """Test sandbox integration with actual tools."""
    
    @pytest.fixture
    def project_root(self, tmp_path):
        """Create a temporary project directory."""
        project = tmp_path / "test_project"
        project.mkdir()
        return str(project)
    
    @pytest.fixture
    def state_with_sandbox(self, project_root):
        """Create a state with sandbox configuration."""
        return KatalystState(
            task="Test task",
            project_root_cwd=project_root,
            auto_approve=True
        )
    
    def test_read_internal_file_allowed(self, project_root, state_with_sandbox):
        """Test reading internal project files."""
        # Create a file in the project
        test_file = os.path.join(project_root, "test.txt")
        with open(test_file, "w") as f:
            f.write("Internal file content")
        
        # Should be able to read it
        result = read(path="test.txt", project_root_cwd=project_root)
        result_data = json.loads(result)
        assert "Internal file content" in result_data["content"]
    
    def test_read_external_file_blocked(self, project_root, state_with_sandbox):
        """Test reading external files is blocked."""
        # Try to read an external file
        result = read(path="/etc/hosts", project_root_cwd=project_root)
        
        # Check for sandbox violation error format
        assert "[SANDBOX_VIOLATION]" in result
        assert "Access denied" in result
        assert "/etc/hosts" in result
        assert "outside the project directory" in result
    
    def test_read_external_file_with_permission(self, project_root):
        """Test reading external files with explicit permission."""
        # Create external test file
        external_file = "/tmp/katalyst_test_external.txt"
        with open(external_file, "w") as f:
            f.write("External content")
        
        try:
            # Create state with allowed external path
            state = KatalystState(
                task=f"Read {external_file}",
                project_root_cwd=project_root,
                allowed_external_paths={external_file}
            )
            
            # In the actual system, the decorator extracts state from graph context
            # For testing, we need to simulate how the decorator would be called
            # The decorator looks for state in kwargs
            from katalyst.coding_agent.tools.read import read
            from functools import wraps
            
            # Create a wrapper that simulates the graph executor passing state
            def simulate_graph_executor(func):
                @wraps(func)
                def wrapper(**kwargs):
                    # Add state to kwargs as the graph executor would
                    kwargs['state'] = state
                    return func(**kwargs)
                return wrapper
            
            # Apply our simulation wrapper
            read_with_state = simulate_graph_executor(read)
            
            # Now test reading the external file
            result = read_with_state(path=external_file, project_root_cwd=project_root)
            result_data = json.loads(result)
            
            # Should succeed with allowed external path
            assert "content" in result_data
            assert "External content" in result_data["content"]
            
        finally:
            if os.path.exists(external_file):
                os.remove(external_file)
    
    def test_write_internal_file_allowed(self, project_root):
        """Test writing to internal project files."""
        # Should be able to write
        result = write(
            path="output.txt",
            content="Test content",
            auto_approve=True,
            project_root_cwd=project_root
        )
        
        # Verify file was created
        output_file = os.path.join(project_root, "output.txt")
        assert os.path.exists(output_file)
        with open(output_file) as f:
            assert f.read() == "Test content"
    
    def test_write_external_file_blocked(self, project_root):
        """Test writing to external files is blocked."""
        # Try to write to external location
        result = write(
            path="/tmp/evil_file.txt",
            content="Should not write",
            auto_approve=True,
            project_root_cwd=project_root
        )
        
        # Check for sandbox violation error format
        assert "[SANDBOX_VIOLATION]" in result
        assert "Access denied" in result
        
        # Verify file was NOT created
        assert not os.path.exists("/tmp/evil_file.txt")
    
    def test_path_traversal_blocked(self, project_root):
        """Test that path traversal attacks are blocked."""
        # Try to escape with ../
        result = read(
            path="../../../etc/passwd",
            project_root_cwd=project_root
        )
        
        # Check for sandbox violation error format
        assert "[SANDBOX_VIOLATION]" in result
        assert "Access denied" in result