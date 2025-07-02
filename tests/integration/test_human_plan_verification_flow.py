import pytest
from unittest.mock import MagicMock, patch, Mock
from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.graph import build_compiled_graph
from katalyst.katalyst_core.utils.error_handling import ErrorType
from katalyst.katalyst_core.utils.models import SubtaskList
from langchain_core.messages import HumanMessage

pytestmark = pytest.mark.integration


# Helper function to create a mock planner
def create_mock_planner(subtasks_list):
    """Create a mock planner that returns the given subtasks."""
    def mock_planner(state):
        # If it's a list of lists, use the appropriate one based on calls
        if isinstance(subtasks_list[0], list):
            # Multiple calls expected
            call_count = getattr(mock_planner, '_call_count', 0)
            subtasks = subtasks_list[min(call_count, len(subtasks_list) - 1)]
            mock_planner._call_count = call_count + 1
        else:
            # Single call expected
            subtasks = subtasks_list
            
        state.task_queue = subtasks
        state.original_plan = subtasks
        state.task_idx = 0
        state.outer_cycles = 0
        state.completed_tasks = []
        state.response = None
        state.error_message = None
        state.plan_feedback = None
        
        # Log the plan
        from langchain_core.messages import AIMessage
        plan_message = f"Generated plan:\\n" + "\\n".join(
            f"{i+1}. {s}" for i, s in enumerate(subtasks)
        )
        state.chat_history.append(AIMessage(content=plan_message))
        
        return state
    
    return mock_planner


class TestHumanPlanVerificationFlow:
    """Integration tests for human-in-the-loop plan verification."""
    
    def test_plan_approval_flow(self):
        """Test complete flow when user approves initial plan."""
        # Create initial state
        state = KatalystState(
            task="Build a calculator",
            project_root_cwd="/test",
            auto_approve=False
        )
        
        # Mock user input - approve plan
        mock_input = MagicMock(return_value="yes")
        state.user_input_fn = mock_input
        
        # Expected subtasks
        expected_subtasks = ["Research the problem", "Implement solution", "Test the code"]
        
        # Mock the planner module
        with patch('katalyst.coding_agent.nodes.planner.planner', create_mock_planner(expected_subtasks)):
            with patch('builtins.print'):  # Suppress output
                # Import and run planner
                from katalyst.coding_agent.nodes.planner import planner
                state = planner(state)
                
                # Verify plan was created
                assert state.task_queue == expected_subtasks
                assert state.original_plan == expected_subtasks
                
                # Run human verification
                from katalyst.coding_agent.nodes.human_plan_verification import human_plan_verification
                state = human_plan_verification(state)
                
                # Verify approval
                assert state.error_message is None
                assert any("approved" in msg.content for msg in state.chat_history if isinstance(msg, HumanMessage))
    
    def test_plan_rejection_replanning_flow(self):
        """Test flow when user rejects plan and provides feedback."""
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
        
        # Expected results for multiple calls
        subtasks_sequence = [
            ["Build calculator", "Done"],
            ["Set up project", "Build calculator with tests", "Add error handling", "Document the code"]
        ]
        
        # Mock the planner module
        with patch('katalyst.coding_agent.nodes.planner.planner', create_mock_planner(subtasks_sequence)):
            with patch('builtins.print'):
                # First planning
                from katalyst.coding_agent.nodes.planner import planner
                state = planner(state)
                assert state.task_queue == subtasks_sequence[0]
                
                # Verification - should reject
                from katalyst.coding_agent.nodes.human_plan_verification import human_plan_verification
                state = human_plan_verification(state)
                
                # Should have rejected with feedback
                assert state.task_queue == []
                assert state.plan_feedback == "Need more detail and tests"
                
                # Second planning with feedback
                state = planner(state)
                assert state.task_queue == subtasks_sequence[1]
                
                # Second verification - should approve
                state = human_plan_verification(state)
                assert state.error_message is None
    
    def test_auto_approve_mode(self):
        """Test that auto-approve mode skips verification."""
        # Create state with auto_approve=True
        state = KatalystState(
            task="Build something",
            project_root_cwd="/test",
            auto_approve=True
        )
        
        # Set up basic plan
        state.task_queue = ["Task 1", "Task 2"]
        
        # Run verification
        from katalyst.coding_agent.nodes.human_plan_verification import human_plan_verification
        state = human_plan_verification(state)
        
        # Should not have cleared task queue
        assert state.task_queue == ["Task 1", "Task 2"]
        assert state.error_message is None


class TestReplannerWithVerification:
    """Test replanner routing to human verification."""
    
    def test_replanner_routes_to_verification(self):
        """Test that replanner routes to human verification when creating new plan."""
        # Create result with new subtasks
        from katalyst.katalyst_core.utils.models import ReplannerOutput
        from katalyst.coding_agent.nodes import replanner as replanner_module
        
        mock_result = ReplannerOutput(
            is_complete=False,
            subtasks=["New task 1", "New task 2"]
        )
        
        # Patch the replanner chain creation and invocation
        with patch.object(replanner_module, 'ChatLiteLLM') as mock_chat, \
             patch.object(replanner_module, 'replanner_prompt') as mock_prompt:
            # Mock the final chain that will be invoked
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = mock_result
            
            # Set up the chain creation: prompt | model.with_structured_output(...)
            mock_model = MagicMock()
            mock_structured_model = MagicMock()
            mock_model.with_structured_output.return_value = mock_structured_model
            mock_chat.return_value = mock_model
            
            # When prompt | structured_model is called, return our mock chain
            mock_prompt.__or__.return_value = mock_chain
            
            # Create state
            state = KatalystState(
                task="Build something",
                project_root_cwd="/test",
                auto_approve=False
            )
            state.completed_tasks = [("Old task", "Done")]
            state.tool_execution_history = []  # Initialize for the new replanner
            
            # Run replanner
            from katalyst.coding_agent.nodes.replanner import replanner
            from katalyst.katalyst_core.routing import route_after_replanner
            
            state = replanner(state)
            
            # Should have new plan
            assert state.task_queue == ["New task 1", "New task 2"]
            
            # Should route to human verification
            next_node = route_after_replanner(state)
            assert next_node == "human_plan_verification"
    
    def test_replanner_routes_to_end_when_done(self):
        """Test that replanner routes to end when goal is complete."""
        # Create result indicating completion
        from katalyst.katalyst_core.utils.models import ReplannerOutput
        from katalyst.coding_agent.nodes import replanner as replanner_module
        
        mock_result = ReplannerOutput(
            is_complete=True,
            subtasks=[]
        )
        
        # Patch the replanner chain creation and invocation
        with patch.object(replanner_module, 'ChatLiteLLM') as mock_chat, \
             patch.object(replanner_module, 'replanner_prompt') as mock_prompt:
            # Mock the final chain that will be invoked
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = mock_result
            
            # Set up the chain creation: prompt | model.with_structured_output(...)
            mock_model = MagicMock()
            mock_structured_model = MagicMock()
            mock_model.with_structured_output.return_value = mock_structured_model
            mock_chat.return_value = mock_model
            
            # When prompt | structured_model is called, return our mock chain
            mock_prompt.__or__.return_value = mock_chain
            
            # Create state
            state = KatalystState(
                task="Build something",
                project_root_cwd="/test"
            )
            state.completed_tasks = [("Task", "Done")]
            state.tool_execution_history = []  # Initialize for the new replanner
            
            # Run replanner
            from katalyst.coding_agent.nodes.replanner import replanner
            from katalyst.katalyst_core.routing import route_after_replanner
            
            state = replanner(state)
            
            # Should have response and empty queue
            assert state.response is not None
            assert state.task_queue == []
            
            # Should route to end
            next_node = route_after_replanner(state)
            assert next_node == "__end__"