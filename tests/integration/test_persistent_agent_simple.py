"""Simple integration test for persistent agent implementation."""
import pytest
from unittest.mock import MagicMock, patch
from katalyst.katalyst_core.state import KatalystState
from katalyst.coding_agent.nodes.planner import planner
from katalyst.coding_agent.nodes.agent_react import agent_react
from katalyst.coding_agent.nodes.advance_pointer import advance_pointer
from langchain_core.agents import AgentFinish
from langchain_core.messages import HumanMessage, AIMessage


@pytest.mark.integration
def test_persistent_agent_state_preservation():
    """Test that agent_executor and messages are preserved in state."""
    # Create initial state
    state = KatalystState(
        task="Test task",
        auto_approve=True,
        project_root_cwd="/test",
        user_input_fn=lambda x: ""
    )
    
    # Simulate planner creating agent_executor
    mock_agent = MagicMock()
    state.agent_executor = mock_agent
    state.messages = [HumanMessage(content="Initial message")]
    state.task_queue = ["Task 1", "Task 2"]
    state.task_idx = 0
    
    # Test that agent_react uses existing agent
    with patch('katalyst.coding_agent.nodes.agent_react.get_logger') as mock_logger:
        # Mock agent response
        mock_agent.invoke.return_value = {
            "messages": state.messages + [AIMessage(content="TASK COMPLETED: Done with task 1")]
        }
        
        # Run agent_react
        result_state = agent_react(state)
        
        # Verify agent was called with messages
        mock_agent.invoke.assert_called_once()
        call_args = mock_agent.invoke.call_args[0][0]
        assert "messages" in call_args
        
        # Verify messages were updated (agent_react adds task message + response)
        assert len(result_state.messages) >= len(state.messages)
        
        # Verify task completion was detected
        assert isinstance(result_state.agent_outcome, AgentFinish)


@pytest.mark.integration
def test_agent_not_recreated_between_tasks():
    """Test that the same agent instance is used for multiple tasks."""
    # Create state with agent
    state = KatalystState(
        task="Test multiple tasks",
        auto_approve=True,
        project_root_cwd="/test",
        user_input_fn=lambda x: ""
    )
    
    mock_agent = MagicMock()
    state.agent_executor = mock_agent
    state.task_queue = ["Task 1", "Task 2"]
    state.task_idx = 0
    state.messages = []
    
    # First task
    mock_agent.invoke.return_value = {
        "messages": [AIMessage(content="TASK COMPLETED: Task 1 done")]
    }
    state = agent_react(state)
    
    # Advance to next task
    state.agent_outcome = AgentFinish(return_values={"output": "Task 1 done"}, log="")
    state = advance_pointer(state)
    
    # Second task - agent should be reused
    mock_agent.invoke.return_value = {
        "messages": state.messages + [AIMessage(content="TASK COMPLETED: Task 2 done")]
    }
    state = agent_react(state)
    
    # Verify agent was called twice (not recreated)
    assert mock_agent.invoke.call_count == 2
    
    # Verify both tasks completed
    assert len(state.completed_tasks) == 1  # First task was recorded
    assert state.task_idx == 1  # Advanced to second task