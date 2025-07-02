"""
Unit tests for tool repetition detection in tool_runner.
"""
import pytest

# Skip this entire test file since repetition_detector has been commented out
pytestmark = pytest.mark.skip("repetition_detector has been commented out in minimal implementation")

from unittest.mock import Mock, MagicMock
from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.error_handling import ErrorType
from langchain_core.agents import AgentAction


class TestToolRunnerRepetition:
    """Test tool repetition detection in tool_runner without full imports."""
    
    def test_state_has_repetition_detector(self):
        """Test that KatalystState includes repetition_detector."""
        state = KatalystState(
            task="Test task",
            project_root_cwd="/test/project"
        )
        
        # Verify repetition_detector exists
        assert hasattr(state, 'repetition_detector')
        assert state.repetition_detector is not None
        
        # Verify it has the expected methods
        assert hasattr(state.repetition_detector, 'check')
        assert hasattr(state.repetition_detector, 'reset')
        assert hasattr(state.repetition_detector, 'get_repetition_count')
    
    def test_repetition_detector_functionality(self):
        """Test basic repetition detector functionality in state."""
        state = KatalystState(
            task="Test task",
            project_root_cwd="/test/project"
        )
        
        # Test identical calls
        tool_name = "read_file"
        tool_input = {"path": "test.py"}
        
        # First 3 calls should be OK
        assert state.repetition_detector.check(tool_name, tool_input) is True
        assert state.repetition_detector.check(tool_name, tool_input) is True
        assert state.repetition_detector.check(tool_name, tool_input) is True
        
        # 4th call should fail
        assert state.repetition_detector.check(tool_name, tool_input) is False
        
        # Get count
        assert state.repetition_detector.get_repetition_count(tool_name, tool_input) == 4
    
    def test_error_type_exists(self):
        """Test that TOOL_REPETITION error type exists."""
        assert hasattr(ErrorType, 'TOOL_REPETITION')
        assert ErrorType.TOOL_REPETITION.value == "TOOL_REPETITION"