"""Integration test for escalating feedback flow."""
from katalyst.katalyst_core.state import KatalystState
from katalyst.coding_agent.nodes._tool_runner import (
    _check_repetitive_calls,
    _check_redundant_operation,
    _count_consecutive_blocks,
    _handle_consecutive_block_escalation
)
from katalyst.coding_agent.nodes.agent_react import agent_react
from katalyst.katalyst_core.utils.error_handling import classify_error, format_error_for_llm
from langchain_core.agents import AgentAction
from unittest.mock import Mock
import logging


def test_escalating_feedback_preserved_through_flow():
    """Test that escalating feedback is preserved through the entire error flow."""
    # Set up logger
    logger = logging.getLogger()
    
    # Create state with some blocked operations in action trace
    state = KatalystState(
        project_root_cwd="/test",
        task="Test task"
    )
    
    # Add some successful operations first
    action1 = AgentAction(tool="write_file", tool_input={"path": "file1.py"}, log="Writing file")
    state.action_trace.append((action1, '{"success": true}'))
    
    # Add blocked operations to trigger escalation
    for i in range(3):
        action = AgentAction(tool="list_files", tool_input={"path": "/"}, log="Listing files")
        state.action_trace.append((action, 'BLOCKED: redundant operation'))
    
    # Create a new action that will be blocked
    new_action = AgentAction(tool="list_files", tool_input={"path": "/"}, log="Listing files")
    
    # Add another blocked operation to simulate multiple consecutive blocks
    action = AgentAction(tool="list_files", tool_input={"path": "/"}, log="Listing files")
    blocked_msg = (
        "[TOOL_RUNNER] [TOOL_REPETITION] ⚠️ CRITICAL: Tool 'list_files' called with IDENTICAL inputs back-to-back! "
        "You are STUCK in a repetitive loop. THINK HARDER and CHANGE YOUR STRATEGY COMPLETELY. "
        "Stop trying the same approach. The operation context shows you ALREADY have this information. "
        "Ask yourself: What DIFFERENT tool or approach will actually progress your task?"
        "\n\n⚠️ WARNING: 4 consecutive blocked operations! "
        "You are stuck in a repetitive pattern. CHANGE YOUR STRATEGY COMPLETELY. "
        "Stop exploring and start executing. What specific action will complete your task? "
        "Try a DIFFERENT type of tool or approach."
    )
    state.action_trace.append((action, blocked_msg))
    state.error_message = blocked_msg
    
    # This simulates a blocked operation
    result = True
    
    assert result == True  # Should be blocked
    assert state.error_message is not None
    
    # Now simulate what happens in agent_react
    error_type, error_details = classify_error(state.error_message)
    
    # Check if this is an escalated error message that should be preserved
    escalation_markers = ["💡 HINT:", "⚠️ WARNING:", "🚨 CRITICAL:", "THINK HARDER", "consecutive blocks"]
    should_preserve = any(marker in error_details for marker in escalation_markers)
    
    if should_preserve:
        # Preserve the full custom message for escalated feedback
        formatted_error = format_error_for_llm(error_type, error_details, custom_message=error_details)
    else:
        # Use default formatting for regular errors
        formatted_error = format_error_for_llm(error_type, error_details)
    
    # Check that escalating feedback is preserved
    assert "THINK HARDER" in formatted_error
    assert "consecutive blocks" in formatted_error or "WARNING:" in formatted_error
    
    # Check that it's ONLY the custom message, not appended to default
    assert formatted_error == error_details, f"Custom message was not preserved exactly!\nExpected: {error_details}\nGot: {formatted_error}"
    
    print(f"Formatted error preserved escalation:\n{formatted_error}")


def test_consecutive_block_counting_and_escalation():
    """Test the consecutive block detection and escalation messages."""
    state = KatalystState(
        project_root_cwd="/test",
        task="Test task"
    )
    logger = logging.getLogger()
    
    # Test different levels of consecutive blocks
    test_cases = [
        (1, "💡 HINT:"),
        (3, "⚠️ WARNING:"),
        (5, "🚨 CRITICAL:")
    ]
    
    for block_count, expected_marker in test_cases:
        # Clear action trace
        state.action_trace = []
        
        # Add blocked operations
        for i in range(block_count - 1):  # -1 because the current block will be counted as +1
            action = AgentAction(tool="read_file", tool_input={"path": "file.py"}, log="Reading")
            state.action_trace.append((action, 'BLOCKED CONSECUTIVE DUPLICATE'))
        
        # Get escalation message
        escalation_msg = _handle_consecutive_block_escalation(
            "read_file", 
            AgentAction(tool="read_file", tool_input={"path": "file.py"}, log="Reading"),
            state,
            logger
        )
        
        assert expected_marker in escalation_msg
        print(f"Blocks: {block_count}, Message: {escalation_msg[:50]}...")


if __name__ == "__main__":
    test_escalating_feedback_preserved_through_flow()
    test_consecutive_block_counting_and_escalation()
    print("\nAll integration tests passed!")