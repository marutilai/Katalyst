import pytest
from unittest.mock import MagicMock, patch
from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.error_handling import ErrorType
from katalyst.coding_agent.nodes.human_plan_verification import human_plan_verification
# MINIMAL: Message imports not needed without chat_history
# from langchain_core.messages import HumanMessage, SystemMessage

pytestmark = pytest.mark.unit


class TestHumanPlanVerification:
    def test_auto_approve_skips_verification(self):
        """Test that auto_approve mode skips human verification."""
        state = KatalystState(
            task="Test task",
            project_root_cwd="/test",
            auto_approve=True,
            task_queue=["Task 1", "Task 2", "Task 3"]
        )
        
        result = human_plan_verification(state)
        
        # MINIMAL: No chat_history to check
        
        # Task queue should remain unchanged
        assert result.task_queue == ["Task 1", "Task 2", "Task 3"]
        assert result.error_message is None
        assert result.response is None
    
    def test_user_approves_plan(self):
        """Test when user approves the plan."""
        state = KatalystState(
            task="Test task",
            project_root_cwd="/test",
            auto_approve=False,
            task_queue=["Task 1", "Task 2", "Task 3"]
        )
        
        # Mock user input
        mock_input = MagicMock(return_value="yes")
        state.user_input_fn = mock_input
        
        with patch('builtins.print'):  # Suppress print output
            result = human_plan_verification(state)
        
        # Should add approval message
        # MINIMAL: No chat_history to check
        
        # Task queue should remain unchanged
        assert result.task_queue == ["Task 1", "Task 2", "Task 3"]
        assert result.error_message is None
        assert result.response is None
    
    def test_user_cancels_operation(self):
        """Test when user cancels the operation."""
        state = KatalystState(
            task="Test task",
            project_root_cwd="/test",
            auto_approve=False,
            task_queue=["Task 1", "Task 2", "Task 3"]
        )
        
        # Mock user input
        mock_input = MagicMock(return_value="cancel")
        state.user_input_fn = mock_input
        
        with patch('builtins.print'):
            result = human_plan_verification(state)
        
        # Should set response and clear task queue
        assert result.response == "Operation cancelled by user"
        assert result.task_queue == []
        # MINIMAL: No chat_history to check
    
    def test_user_rejects_with_feedback(self):
        """Test when user provides feedback for a better plan."""
        state = KatalystState(
            task="Test task",
            project_root_cwd="/test",
            auto_approve=False,
            task_queue=["Task 1", "Task 2", "Task 3"]
        )
        
        # Mock user input - direct feedback
        mock_input = MagicMock(return_value="Please include tests in the plan")
        state.user_input_fn = mock_input
        
        with patch('builtins.print'):
            result = human_plan_verification(state)
        
        # Should clear task queue and set feedback
        assert result.task_queue == []
        assert result.plan_feedback == "Please include tests in the plan"
        assert f"[{ErrorType.REPLAN_REQUESTED.value}]" in result.error_message
        # MINIMAL: No chat_history to check
    
    def test_user_says_no_then_provides_feedback(self):
        """Test when user says 'no' and then provides specific feedback."""
        state = KatalystState(
            task="Test task",
            project_root_cwd="/test",
            auto_approve=False,
            task_queue=["Task 1", "Task 2", "Task 3"]
        )
        
        # Mock user input - first 'no', then feedback
        responses = ["no", "Add error handling steps"]
        mock_input = MagicMock(side_effect=responses)
        state.user_input_fn = mock_input
        
        with patch('builtins.print'):
            result = human_plan_verification(state)
        
        # Should prompt for feedback after 'no'
        assert mock_input.call_count == 2
        
        # Should clear task queue and set feedback
        assert result.task_queue == []
        assert result.plan_feedback == "Add error handling steps"
        assert f"[{ErrorType.REPLAN_REQUESTED.value}]" in result.error_message
        # MINIMAL: No chat_history to check
    
    def test_empty_task_queue(self):
        """Test behavior with empty task queue."""
        state = KatalystState(
            task="Test task",
            project_root_cwd="/test",
            auto_approve=False,
            task_queue=[]
        )
        
        mock_input = MagicMock(return_value="yes")
        state.user_input_fn = mock_input
        
        with patch('builtins.print'):
            result = human_plan_verification(state)
        
        # Should still work with empty queue
        assert result.task_queue == []
        # MINIMAL: No chat_history to check


class TestRoutingAfterVerification:
    """Test the routing logic after human verification."""
    
    def test_route_to_end_when_cancelled(self):
        """Test routing to END when user cancelled."""
        from katalyst.katalyst_core.routing import route_after_verification
        from langgraph.graph import END
        
        state = KatalystState(
            task="Test",
            project_root_cwd="/test",
            response="Operation cancelled by user",
            task_queue=[]
        )
        
        assert route_after_verification(state) == END
    
    def test_route_to_planner_with_feedback(self):
        """Test routing to planner when user provided feedback."""
        from katalyst.katalyst_core.routing import route_after_verification
        
        state = KatalystState(
            task="Test",
            project_root_cwd="/test",
            error_message=f"[{ErrorType.REPLAN_REQUESTED.value}] User feedback: Make it better",
            task_queue=[]
        )
        
        assert route_after_verification(state) == "planner"
    
    def test_route_to_agent_react_when_approved(self):
        """Test routing to agent_react when plan approved."""
        from katalyst.katalyst_core.routing import route_after_verification
        
        state = KatalystState(
            task="Test",
            project_root_cwd="/test",
            task_queue=["Task 1", "Task 2"]
        )
        
        assert route_after_verification(state) == "executor"
    
    def test_route_to_end_fallback(self):
        """Test fallback routing to END."""
        from katalyst.katalyst_core.routing import route_after_verification
        from langgraph.graph import END
        
        state = KatalystState(
            task="Test",
            project_root_cwd="/test",
            # No response, no error, no tasks
        )
        
        assert route_after_verification(state) == END