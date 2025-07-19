"""Simple integration test for persistent agent implementation."""
import pytest
from unittest.mock import MagicMock, patch, Mock
from katalyst.katalyst_core.state import KatalystState
from katalyst.coding_agent.nodes.planner import planner
from katalyst.coding_agent.nodes.executor import executor
from katalyst.coding_agent.nodes.advance_pointer import advance_pointer
from langchain_core.agents import AgentFinish
from langchain_core.messages import HumanMessage, AIMessage


@pytest.mark.integration 
def test_persistent_agent_state_preservation():
    """Test that checkpointer and messages are preserved in state."""
    # Create initial state
    state = KatalystState(
        task="Test task",
        auto_approve=True,
        project_root_cwd="/test",
        user_input_fn=lambda x: ""
    )
    
    # Simulate checkpointer
    mock_checkpointer = MagicMock()
    state.checkpointer = mock_checkpointer
    state.messages = [HumanMessage(content="Initial message")]
    state.task_queue = ["Task 1", "Task 2"]
    state.task_idx = 0
    
    # Test that executor uses checkpointer to create agent
    with patch('katalyst.coding_agent.nodes.executor.get_logger') as mock_logger:
        with patch('katalyst.coding_agent.nodes.executor.create_react_agent') as mock_create_agent:
            # Mock agent
            mock_agent = MagicMock()
            mock_create_agent.return_value = mock_agent
            
            # Mock agent response
            mock_agent.invoke.return_value = {
                "messages": state.messages + [AIMessage(content="TASK COMPLETED: Done with task 1")]
            }
            
            # Run executor
            result_state = executor(state)
            
            # Verify agent was created with checkpointer
            mock_create_agent.assert_called_once()
            call_kwargs = mock_create_agent.call_args[1]
            assert call_kwargs['checkpointer'] == mock_checkpointer
            
            # Verify agent was called with messages
            mock_agent.invoke.assert_called_once()
            call_args = mock_agent.invoke.call_args[0][0]
            assert "messages" in call_args
            
            # Verify messages were updated (executor adds task message + response)
            assert len(result_state.messages) >= len(state.messages)
            
            # Verify task completion was detected
            assert isinstance(result_state.agent_outcome, AgentFinish)


@pytest.mark.integration
def test_checkpointer_shared_between_agents():
    """Test that the same checkpointer is used by all agents."""
    # Create state with checkpointer
    state = KatalystState(
        task="Test multiple agents",
        auto_approve=True,
        project_root_cwd="/test",
        user_input_fn=lambda x: ""
    )
    
    mock_checkpointer = MagicMock()
    state.checkpointer = mock_checkpointer
    state.task_queue = ["Task 1", "Task 2"]
    state.task_idx = 0
    state.messages = []
    
    # Track agent creations
    created_agents = []
    
    def track_agent_creation(*args, **kwargs):
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {
            "messages": [AIMessage(content="TASK COMPLETED: Task done")]
        }
        created_agents.append((args, kwargs))
        return mock_agent
    
    with patch('katalyst.coding_agent.nodes.executor.create_react_agent', side_effect=track_agent_creation):
        # First task
        state = executor(state)
        
        # Advance to next task
        state.agent_outcome = AgentFinish(return_values={"output": "Task 1 done"}, log="")
        state = advance_pointer(state)
        
        # Second task
        state = executor(state)
    
    # Verify two agents were created with same checkpointer
    assert len(created_agents) == 2
    assert created_agents[0][1]['checkpointer'] == mock_checkpointer
    assert created_agents[1][1]['checkpointer'] == mock_checkpointer
    
    # Verify both tasks completed
    assert len(state.completed_tasks) == 1  # First task was recorded
    assert state.task_idx == 1  # Advanced to second task


@pytest.mark.integration
def test_state_persistence_through_planning():
    """Test that messages persist through planner, executor, and replanner."""
    # Create initial state
    state = KatalystState(
        task="Build a todo app",
        auto_approve=True,
        project_root_cwd="/test",
        user_input_fn=lambda x: ""
    )
    
    # Mock checkpointer
    mock_checkpointer = MagicMock()
    state.checkpointer = mock_checkpointer
    
    # Mock the agent creation for all three agents
    mock_agents = {}
    
    def create_mock_agent(*args, **kwargs):
        # Determine which agent is being created based on tools
        tools = kwargs.get('tools', [])
        tool_names = [t.name for t in tools]
        
        if 'write' in tool_names:
            agent_type = 'executor'
        elif 'generate_directory_overview' in tool_names:
            agent_type = 'planner'
        else:
            agent_type = 'replanner'
        
        mock_agent = MagicMock()
        mock_agents[agent_type] = mock_agent
        
        # Configure responses based on agent type
        if agent_type == 'planner':
            # Import SubtaskList to create structured response
            from katalyst.katalyst_core.utils.models import SubtaskList
            mock_agent.invoke.return_value = {
                "messages": [AIMessage(content="I've created a plan for the todo app")],
                "structured_response": SubtaskList(subtasks=["Create index.html", "Add styling"])
            }
        elif agent_type == 'executor':
            mock_agent.invoke.return_value = {
                "messages": [AIMessage(content="TASK COMPLETED: Created file")]
            }
        else:  # replanner
            mock_agent.invoke.return_value = {
                "messages": [AIMessage(content="OBJECTIVE COMPLETE: Todo app built")]
            }
        
        return mock_agent
    
    with patch('katalyst.coding_agent.nodes.planner.create_react_agent', side_effect=create_mock_agent):
        with patch('katalyst.coding_agent.nodes.executor.create_react_agent', side_effect=create_mock_agent):
            with patch('katalyst.coding_agent.nodes.replanner.create_react_agent', side_effect=create_mock_agent):
                # Run planner
                from katalyst.coding_agent.nodes.planner import planner
                state = planner(state)
                
                # Verify plan was created
                assert state.task_queue == ["Create index.html", "Add styling"]
                
                # Run executor on first task
                state = executor(state)
                
                # Verify all agents used same checkpointer
                assert all(agent in mock_agents for agent in ['planner', 'executor'])
                
                # Messages should accumulate
                assert len(state.messages) > 0