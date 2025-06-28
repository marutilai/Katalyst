import pytest
from unittest.mock import MagicMock, patch
from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.graph import build_compiled_graph
from langchain_core.messages import HumanMessage

pytestmark = pytest.mark.integration


class TestHumanPlanVerificationFlow:
    """Integration tests for human-in-the-loop plan verification."""
    
    @patch('katalyst.coding_agent.nodes.planner.get_llm_client')
    def test_plan_approval_flow(self, mock_llm):
        """Test complete flow when user approves initial plan."""
        # Mock LLM to generate a plan
        mock_response = MagicMock()
        mock_response.subtasks = ["Research the problem", "Implement solution", "Test the code"]
        mock_llm.return_value.chat.completions.create.return_value = mock_response
        
        # Create initial state
        state = KatalystState(
            task="Build a calculator",
            project_root_cwd="/test",
            auto_approve=False
        )
        
        # Mock user input - approve plan
        mock_input = MagicMock(return_value="yes")
        state.user_input_fn = mock_input
        
        # Build and run graph
        graph = build_compiled_graph()
        
        with patch('builtins.print'):  # Suppress output
            # Run just through plan verification
            # Note: We'd need to mock more for full execution
            nodes = []
            for node in ['planner', 'human_plan_verification']:
                if node == 'planner':
                    from katalyst.coding_agent.nodes.planner import planner
                    state = planner(state)
                    nodes.append('planner')
                elif node == 'human_plan_verification':
                    from katalyst.coding_agent.nodes.human_plan_verification import human_plan_verification
                    state = human_plan_verification(state)
                    nodes.append('human_plan_verification')
        
        # Verify plan was created and approved
        assert state.task_queue == ["Research the problem", "Implement solution", "Test the code"]
        assert state.error_message is None
        assert any("approved" in msg.content for msg in state.chat_history if isinstance(msg, HumanMessage))
    
    @patch('katalyst.coding_agent.nodes.planner.get_llm_client')
    def test_plan_rejection_replanning_flow(self, mock_llm):
        """Test flow when user rejects plan and provides feedback."""
        # Mock LLM responses - first plan, then improved plan
        first_response = MagicMock()
        first_response.subtasks = ["Build calculator", "Done"]
        
        second_response = MagicMock()
        second_response.subtasks = ["Set up project", "Build calculator with tests", "Add error handling", "Document the code"]
        
        mock_llm.return_value.chat.completions.create.side_effect = [first_response, second_response]
        
        # Create initial state
        state = KatalystState(
            task="Build a calculator",
            project_root_cwd="/test",
            auto_approve=False
        )
        
        # Mock user input - reject first plan, approve second
        responses = ["Need more detail and tests", "yes"]
        mock_input = MagicMock(side_effect=responses)
        state.user_input_fn = mock_input
        
        with patch('builtins.print'):
            # First planning and verification
            from katalyst.coding_agent.nodes.planner import planner
            state = planner(state)
            assert state.task_queue == ["Build calculator", "Done"]
            
            from katalyst.coding_agent.nodes.human_plan_verification import human_plan_verification
            state = human_plan_verification(state)
            
            # Should have rejected with feedback
            assert state.task_queue == []
            assert "[REPLAN_REQUESTED]" in state.error_message
            assert "Need more detail and tests" in state.error_message
            
            # Clear error for replanning
            state.error_message = None
            
            # Second planning with feedback in history
            state = planner(state)
            assert state.task_queue == ["Set up project", "Build calculator with tests", "Add error handling", "Document the code"]
            
            # Second verification - approve
            state = human_plan_verification(state)
            assert state.task_queue == ["Set up project", "Build calculator with tests", "Add error handling", "Document the code"]
            assert state.error_message is None
    
    def test_auto_approve_mode(self):
        """Test that auto_approve mode bypasses verification."""
        state = KatalystState(
            task="Test task",
            project_root_cwd="/test",
            auto_approve=True,
            task_queue=["Task 1", "Task 2"]
        )
        
        from katalyst.coding_agent.nodes.human_plan_verification import human_plan_verification
        
        # Should not prompt for input
        with patch('builtins.print') as mock_print:
            result = human_plan_verification(state)
        
        # Should not have printed verification prompt
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert not any("KATALYST PLAN VERIFICATION" in call for call in print_calls)
        
        # Should proceed with plan
        assert result.task_queue == ["Task 1", "Task 2"]
        assert "automatically approved" in result.chat_history[-1].content


class TestReplannerWithVerification:
    """Test that replanner also routes through verification."""
    
    def test_replanner_routes_to_verification(self):
        """Test that new plans from replanner go through verification."""
        from katalyst.katalyst_core.routing import route_after_replanner
        
        state = KatalystState(
            task="Test",
            project_root_cwd="/test",
            task_queue=["New task 1", "New task 2"],  # Replanner created new tasks
            response=None
        )
        
        # Should route to human verification
        assert route_after_replanner(state) == "human_plan_verification"
    
    def test_replanner_routes_to_end_when_done(self):
        """Test replanner routes to END when task complete."""
        from katalyst.katalyst_core.routing import route_after_replanner
        from langgraph.graph import END
        
        state = KatalystState(
            task="Test",
            project_root_cwd="/test",
            response="Task completed successfully"
        )
        
        assert route_after_replanner(state) == END