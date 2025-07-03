#!/usr/bin/env python3
"""
Test script for the /init command to verify it generates complete KATALYST.md
"""

import pytest
from katalyst.app.cli.commands import handle_init_command


@pytest.mark.integration
def test_init_command():
    """Test the /init command setup and task creation (without running the agent)"""
    from unittest.mock import Mock, patch, MagicMock
    
    # Create a mock graph that captures the invoke call
    mock_graph = Mock()
    mock_result = {
        "response": "Successfully generated KATALYST.md",
        "completed_tasks": [("Generate developer guide", "Created comprehensive KATALYST.md")]
    }
    mock_graph.invoke.return_value = mock_result
    
    # Mock config
    mock_config = {
        "configurable": {"thread_id": "test-init-thread"},
        "recursion_limit": 250
    }
    
    # Test that handle_init_command properly sets up the task
    with patch('katalyst.app.cli.commands.console') as mock_console:
        # Call handle_init_command with mocked graph
        handle_init_command(mock_graph, mock_config)
        
        # Verify the graph was invoked with correct parameters
        mock_graph.invoke.assert_called_once()
        
        # Check the task input
        call_args = mock_graph.invoke.call_args[0][0]
        assert "task" in call_args
        assert "KATALYST.md" in call_args["task"]
        assert "developer guide" in call_args["task"].lower()
        
        # Verify console output
        mock_console.print.assert_called()
        console_output = str(mock_console.print.call_args_list)
        assert "developer guide" in console_output.lower()


@pytest.mark.skip(reason="This is an e2e test that requires LLM - move to separate e2e test suite")
def test_init_command_e2e():
    """End-to-end test for the /init command (requires actual LLM)"""
    # Original test code here - this would be moved to an e2e test file
    pass


if __name__ == "__main__":
    print("Run with pytest instead: pytest tests/integration/app/test_init_command.py")