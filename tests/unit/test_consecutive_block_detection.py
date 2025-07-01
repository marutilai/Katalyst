"""Test consecutive block detection in tool runner."""
import pytest
from unittest.mock import Mock
from katalyst.katalyst_core.state import KatalystState
from katalyst.coding_agent.nodes.tool_runner import _count_consecutive_blocks
from langchain_core.agents import AgentAction


def test_count_consecutive_blocks_empty_trace():
    """Test counting with empty action trace."""
    state = KatalystState(
        project_root_cwd="/test",
        task="Test task"
    )
    assert _count_consecutive_blocks(state) == 0


def test_count_consecutive_blocks_no_blocks():
    """Test counting with no blocked operations."""
    state = KatalystState(
        project_root_cwd="/test",
        task="Test task"
    )
    
    # Add successful operations
    action1 = AgentAction(tool="read_file", tool_input={"path": "file1.py"}, log="Reading file")
    state.action_trace.append((action1, '{"success": true, "content": "file content"}'))
    
    action2 = AgentAction(tool="write_file", tool_input={"path": "file2.py"}, log="Writing file")
    state.action_trace.append((action2, '{"success": true}'))
    
    assert _count_consecutive_blocks(state) == 0


def test_count_consecutive_blocks_single_block():
    """Test counting with one blocked operation."""
    state = KatalystState(
        project_root_cwd="/test",
        task="Test task"
    )
    
    # Add a successful operation followed by a blocked one
    action1 = AgentAction(tool="read_file", tool_input={"path": "file1.py"}, log="Reading file")
    state.action_trace.append((action1, '{"success": true}'))
    
    action2 = AgentAction(tool="list_files", tool_input={"path": "/"}, log="Listing files")
    state.action_trace.append((action2, 'BLOCKED CONSECUTIVE DUPLICATE: list_files - This is a waste!'))
    
    assert _count_consecutive_blocks(state) == 1


def test_count_consecutive_blocks_multiple():
    """Test counting with multiple consecutive blocked operations."""
    state = KatalystState(
        project_root_cwd="/test",
        task="Test task"
    )
    
    # Add a successful operation
    action1 = AgentAction(tool="read_file", tool_input={"path": "file1.py"}, log="Reading file")
    state.action_trace.append((action1, '{"success": true}'))
    
    # Add multiple blocked operations
    action2 = AgentAction(tool="list_files", tool_input={"path": "/"}, log="Listing files")
    state.action_trace.append((action2, 'REDUNDANT OPERATION BLOCKED: Tool list_files was already executed'))
    
    action3 = AgentAction(tool="list_files", tool_input={"path": "/"}, log="Listing files")
    state.action_trace.append((action3, 'BLOCKED CONSECUTIVE DUPLICATE: list_files'))
    
    action4 = AgentAction(tool="read_file", tool_input={"path": "file1.py"}, log="Reading file")
    state.action_trace.append((action4, 'Tool repetition detected: read_file has been called 3 times'))
    
    assert _count_consecutive_blocks(state) == 3


def test_count_consecutive_blocks_interrupted():
    """Test counting stops at first successful operation."""
    state = KatalystState(
        project_root_cwd="/test",
        task="Test task"
    )
    
    # Add blocked operations followed by success followed by more blocks
    action1 = AgentAction(tool="list_files", tool_input={"path": "/"}, log="Listing files")
    state.action_trace.append((action1, 'BLOCKED: redundant operation'))
    
    action2 = AgentAction(tool="list_files", tool_input={"path": "/"}, log="Listing files")
    state.action_trace.append((action2, 'BLOCKED: redundant operation'))
    
    # Successful operation breaks the chain
    action3 = AgentAction(tool="write_file", tool_input={"path": "new.py"}, log="Writing file")
    state.action_trace.append((action3, '{"success": true}'))
    
    # More blocks after success
    action4 = AgentAction(tool="list_files", tool_input={"path": "/"}, log="Listing files")
    state.action_trace.append((action4, 'BLOCKED CONSECUTIVE DUPLICATE'))
    
    action5 = AgentAction(tool="list_files", tool_input={"path": "/"}, log="Listing files")
    state.action_trace.append((action5, 'Tool has been called 5 times'))
    
    # Should only count the last 2 blocks (after the successful operation)
    assert _count_consecutive_blocks(state) == 2


if __name__ == "__main__":
    test_count_consecutive_blocks_empty_trace()
    test_count_consecutive_blocks_no_blocks()
    test_count_consecutive_blocks_single_block()
    test_count_consecutive_blocks_multiple()
    test_count_consecutive_blocks_interrupted()
    print("All tests passed!")