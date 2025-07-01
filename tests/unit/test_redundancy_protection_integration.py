"""
Integration test showing all three levels of redundancy protection:
1. Consecutive duplicate detection
2. Repetition threshold detection  
3. Deterministic state tracking
"""
import pytest
from unittest.mock import Mock
from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.tool_repetition_detector import ToolRepetitionDetector
from katalyst.katalyst_core.utils.operation_context import OperationContext
from katalyst.coding_agent.nodes.tool_runner import (
    _check_repetitive_calls,
    _check_redundant_operation,
)
from langchain_core.agents import AgentAction


def test_three_levels_of_protection():
    """Test that all three protection levels work together."""
    # Set up state with both detectors
    state = KatalystState(
        repetition_detector=ToolRepetitionDetector(repetition_threshold=3),
        operation_context=OperationContext(),
        task_queue=["Test task"],
        task_idx=0,
        task="Test task",
        project_root_cwd="/test"
    )
    logger = Mock()
    
    # Create test action
    def make_action(tool, input_dict):
        return AgentAction(tool=tool, tool_input=input_dict, log="test")
    
    # ========== Level 1: First call succeeds ==========
    action1 = make_action("read_file", {"path": "test.py"})
    assert _check_repetitive_calls("read_file", {"path": "test.py"}, action1, state, logger) is False
    
    # Simulate successful execution by adding to operation context
    state.operation_context.add_tool_operation(
        tool_name="read_file",
        tool_input={"path": "test.py"},
        success=True
    )
    
    # ========== Level 2: Second call passes (under threshold) ==========
    action2 = make_action("read_file", {"path": "test.py"})
    # Second call should pass (threshold is 3)
    assert _check_repetitive_calls("read_file", {"path": "test.py"}, action2, state, logger) is False
    # But it's tracked as a repetition
    
    # ========== Interleave with different operation ==========
    action3 = make_action("list_files", {"path": "./"})
    assert _check_repetitive_calls("list_files", {"path": "./"}, action3, state, logger) is False
    
    # ========== Level 3: Deterministic blocking ==========
    action4 = make_action("read_file", {"path": "test.py"})
    # Not consecutive anymore, but should be blocked by deterministic check
    assert _check_repetitive_calls("read_file", {"path": "test.py"}, action4, state, logger) is False
    assert _check_redundant_operation("read_file", {"path": "test.py"}, action4, state, logger) is True
    assert "REDUNDANT OPERATION BLOCKED" in state.error_message
    state.error_message = None
    
    # ========== Writes are never redundant ==========
    write_action = make_action("write_to_file", {"path": "test.py", "content": "data"})
    assert _check_redundant_operation("write_to_file", {"path": "test.py", "content": "data"}, 
                                     write_action, state, logger) is False
    
    # ========== Different file is allowed ==========
    action5 = make_action("read_file", {"path": "other.py"})
    assert _check_repetitive_calls("read_file", {"path": "other.py"}, action5, state, logger) is False
    assert _check_redundant_operation("read_file", {"path": "other.py"}, action5, state, logger) is False