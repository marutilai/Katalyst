"""
Integration tests for tool repetition detection in agent flow.
"""
import pytest
from unittest.mock import Mock, patch
from katalyst.katalyst_core.state import KatalystState
from katalyst.coding_agent.nodes.tool_runner import tool_runner
from langchain_core.agents import AgentAction


@pytest.fixture
def mock_state():
    """Create a mock state for testing."""
    state = KatalystState(
        task="Test task",
        project_root_cwd="/test/project"
    )
    return state


@pytest.fixture
def mock_tool_registry():
    """Create a mock tool registry."""
    mock_tool = Mock(return_value='{"success": true, "result": "test"}')
    return {"test_tool": mock_tool}


@pytest.mark.skip(reason="Tool repetition detection removed in minimal implementation")
class TestToolRepetitionDetectionIntegration:
    """Integration tests for tool repetition detection."""
    
    @patch("katalyst.coding_agent.nodes.tool_runner.REGISTERED_TOOL_FUNCTIONS_MAP")
    def test_repetition_blocks_after_threshold(self, mock_registry, mock_state):
        """Test that repetitive tool calls are blocked after threshold."""
        # Setup mock tool
        mock_tool = Mock(return_value='{"success": true}')
        # Add __code__ attribute for tool_runner compatibility
        mock_tool.__code__ = Mock(co_varnames=["path"])
        mock_registry.__getitem__.return_value = mock_tool
        mock_registry.get.return_value = mock_tool
        
        # Create identical agent actions
        action = AgentAction(
            tool="read_file",
            tool_input={"path": "test.py"},
            log="Reading test.py"
        )
        
        # First 3 calls should succeed (default threshold is 3)
        for i in range(3):
            mock_state.agent_outcome = action
            result_state = tool_runner(mock_state)
            
            # Tool should be executed
            assert result_state.error_message is None
            assert len(result_state.action_trace) == i + 1
            # Check that action trace contains success
            assert "success" in result_state.action_trace[-1][1]
        
        # 4th call should be blocked
        mock_state.agent_outcome = action
        result_state = tool_runner(mock_state)
        
        # Tool should not be executed
        assert result_state.error_message is not None
        assert "[TOOL_REPETITION]" in result_state.error_message
        # The message will be for consecutive duplicate since it's the 4th identical call in a row
        assert ("back-to-back" in result_state.error_message or 
                "has been called" in result_state.error_message)
        assert result_state.agent_outcome is None
        
        # Verify tool was only called 3 times
        assert mock_tool.call_count == 3
    
    @patch("katalyst.coding_agent.nodes.tool_runner.REGISTERED_TOOL_FUNCTIONS_MAP")
    def test_different_inputs_not_blocked(self, mock_registry, mock_state):
        """Test that same tool with different inputs is not blocked."""
        # Setup mock tool
        mock_tool = Mock(return_value='{"success": true}')
        mock_tool.__code__ = Mock(co_varnames=["path"])
        mock_registry.__getitem__.return_value = mock_tool
        mock_registry.get.return_value = mock_tool
        
        # Create different agent actions for same tool
        for i in range(5):
            action = AgentAction(
                tool="read_file",
                tool_input={"path": f"test{i}.py"},  # Different file each time
                log=f"Reading test{i}.py"
            )
            mock_state.agent_outcome = action
            result_state = tool_runner(mock_state)
            
            # All calls should succeed
            assert result_state.error_message is None
            assert len(result_state.action_trace) == i + 1
        
        # Verify all calls were made
        assert mock_tool.call_count == 5
    
    @patch("katalyst.coding_agent.nodes.tool_runner.REGISTERED_TOOL_FUNCTIONS_MAP")
    def test_repetition_detector_reset_between_tasks(self, mock_registry, mock_state):
        """Test that repetition detector is reset between tasks."""
        from katalyst.coding_agent.nodes.advance_pointer import advance_pointer
        from langchain_core.agents import AgentFinish
        
        # Setup mock tool
        mock_tool = Mock(return_value='{"success": true}')
        mock_tool.__code__ = Mock(co_varnames=["path"])
        mock_registry.__getitem__.return_value = mock_tool
        mock_registry.get.return_value = mock_tool
        
        # Setup task queue
        mock_state.task_queue = ["Task 1", "Task 2"]
        mock_state.task_idx = 0
        
        # Make 3 calls for the same tool in task 1
        action = AgentAction(
            tool="read_file",
            tool_input={"path": "test.py"},
            log="Reading test.py"
        )
        
        for _ in range(3):
            mock_state.agent_outcome = action
            tool_runner(mock_state)
        
        # Complete task 1
        mock_state.agent_outcome = AgentFinish(
            return_values={"output": "Task 1 completed"},
            log="Done"
        )
        result_state = advance_pointer(mock_state)
        
        # Verify detector was reset
        assert len(result_state.repetition_detector.recent_calls) == 0
        assert result_state.task_idx == 1
        
        # Should be able to use the same tool again in task 2
        mock_state.agent_outcome = action
        result_state = tool_runner(mock_state)
        
        # Should succeed
        assert result_state.error_message is None
        assert mock_tool.call_count == 4  # 3 from task 1, 1 from task 2
    
    @patch("katalyst.coding_agent.nodes.tool_runner.REGISTERED_TOOL_FUNCTIONS_MAP")
    def test_complex_input_repetition(self, mock_registry, mock_state):
        """Test repetition detection with complex nested inputs."""
        # Setup mock tool
        mock_tool = Mock(return_value='{"success": true}')
        mock_tool.__code__ = Mock(co_varnames=["path", "options", "filters"])
        mock_registry.__getitem__.return_value = mock_tool
        mock_registry.get.return_value = mock_tool
        
        # Complex input with nested structures
        complex_input = {
            "path": "project/src/main.py",
            "options": {
                "encoding": "utf-8",
                "line_range": [1, 100]
            },
            "filters": ["imports", "functions"]
        }
        
        action = AgentAction(
            tool="analyze_file",
            tool_input=complex_input,
            log="Analyzing file"
        )
        
        # Should handle complex inputs correctly
        for i in range(3):
            mock_state.agent_outcome = action
            result_state = tool_runner(mock_state)
            assert result_state.error_message is None
        
        # 4th call should be blocked
        mock_state.agent_outcome = action
        result_state = tool_runner(mock_state)
        assert "[TOOL_REPETITION]" in result_state.error_message
    
    def test_error_message_format(self, mock_state):
        """Test that error messages are properly formatted for the LLM."""
        from katalyst.katalyst_core.utils.error_handling import format_error_for_llm, ErrorType
        
        error_msg = format_error_for_llm(
            ErrorType.TOOL_REPETITION,
            "Tool 'read_file' has been called 3 times with identical inputs."
        )
        
        assert "Repetitive tool call detected" in error_msg
        assert "try a different approach" in error_msg
        assert "different tool" in error_msg