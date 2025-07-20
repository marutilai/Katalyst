import pytest
from unittest.mock import Mock, patch
from katalyst.katalyst_core.state import KatalystState
from katalyst.coding_agent.nodes.planner import planner
from langchain_core.agents import AgentAction
import json

@pytest.mark.skip(reason="Adaptive planning removed in minimal implementation")
class TestAdaptivePlanning:
    """Test the adaptive planning system with dynamic task creation."""
    
    @pytest.fixture
    def initial_state(self):
        """Create initial state for testing."""
        return KatalystState(
            task="Create a simple todo app",
            project_root_cwd="/test/project",
            auto_approve=True,
            task_queue=[],
            created_subtasks={}
        )
    
    def test_goal_oriented_planner_output(self, initial_state):
        """Test that planner produces goal-oriented tasks."""
        # Mock the LLM response for planner
        mock_subtasks = [
            "Set up project structure and configuration",
            "Implement Todo model with CRUD operations",
            "Create REST API endpoints",
            "Write test suite"
        ]
        
        with patch('katalyst.coding_agent.nodes.planner.get_llm_client') as mock_llm:
            # Setup mock to return goal-oriented tasks
            mock_response = Mock()
            mock_response.subtasks = mock_subtasks
            mock_llm.return_value.chat.completions.create.return_value = mock_response
            
            # Run planner
            result_state = planner(initial_state)
            
            # Verify goal-oriented tasks were created
            assert len(result_state.task_queue) == 4
            assert "Set up project structure" in result_state.task_queue[0]
            assert "model" in result_state.task_queue[1].lower()
            assert "API" in result_state.task_queue[2]
            
            # Verify no tool-specific language
            for task in result_state.task_queue:
                assert "write_to_file" not in task.lower()
                assert "use " not in task.lower()
    
    def test_create_subtask_integration(self, initial_state):
        """Test create_subtask tool integration with tool_runner."""
        # Set up state with a current task
        initial_state.task_queue = [
            "Implement models for the application",
            "Create API endpoints"
        ]
        initial_state.original_plan = [
            "Implement models for the application",
            "Create API endpoints"
        ]
        initial_state.task_idx = 0
        
        # Create agent action for create_subtask
        agent_action = AgentAction(
            tool="create_subtask",
            tool_input={
                "task_description": "Implement User model with authentication",
                "reason": "Found multiple models needed, breaking them down",
                "insert_position": "after_current"
            },
            log="Creating subtask for User model"
        )
        initial_state.agent_outcome = agent_action
        
        # Mock the tool function registry
        with patch('katalyst.coding_agent.nodes.tool_runner.REGISTERED_TOOL_FUNCTIONS_MAP') as mock_tools:
            from katalyst.coding_agent.tools.create_subtask import create_subtask
            mock_tools.get.return_value = create_subtask
            
            # Run tool_runner
            result_state = tool_runner(initial_state)
            
            # Verify subtask was added to queue
            assert len(result_state.task_queue) == 3  # Original 2 + 1 new
            assert "Implement User model" in result_state.task_queue[1]
            
            # Verify tracking
            assert 0 in result_state.created_subtasks
            assert len(result_state.created_subtasks[0]) == 1
            assert "Implement User model" in result_state.created_subtasks[0][0]
    
    def test_subtask_limit_enforcement(self, initial_state):
        """Test that subtask creation limit is enforced."""
        initial_state.task_queue = ["Create all models"]
        initial_state.task_idx = 0
        initial_state.created_subtasks = {0: ["Task1", "Task2", "Task3", "Task4", "Task5"]}
        
        # Try to create 6th subtask
        agent_action = AgentAction(
            tool="create_subtask",
            tool_input={
                "task_description": "Task6",
                "reason": "Another subtask",
                "insert_position": "after_current"
            },
            log="Creating 6th subtask"
        )
        initial_state.agent_outcome = agent_action
        
        with patch('katalyst.coding_agent.nodes.tool_runner.REGISTERED_TOOL_FUNCTIONS_MAP') as mock_tools:
            from katalyst.coding_agent.tools.create_subtask import create_subtask
            mock_tools.get.return_value = create_subtask
            
            # Run tool_runner
            result_state = tool_runner(initial_state)
            
            # Check the observation for limit error
            _, observation = result_state.action_trace[-1]
            obs_data = json.loads(observation)
            
            assert obs_data["success"] is False
            assert "Maximum subtasks" in obs_data["error"]
            
            # Verify no new task was added
            assert len(result_state.task_queue) == 1
    
    def test_subtask_insertion_positions(self, initial_state):
        """Test different insertion positions for subtasks."""
        initial_state.task_queue = ["Task A", "Task B", "Task C"]
        initial_state.original_plan = ["Task A", "Task B", "Task C"]
        initial_state.task_idx = 0
        
        # Test after_current position
        agent_action = AgentAction(
            tool="create_subtask",
            tool_input={
                "task_description": "Task A.1",
                "reason": "Subtask of A",
                "insert_position": "after_current"
            },
            log="Creating subtask after current"
        )
        initial_state.agent_outcome = agent_action
        
        with patch('katalyst.coding_agent.nodes.tool_runner.REGISTERED_TOOL_FUNCTIONS_MAP') as mock_tools:
            from katalyst.coding_agent.tools.create_subtask import create_subtask
            mock_tools.get.return_value = create_subtask
            
            result_state = tool_runner(initial_state)
            
            # Verify insertion position
            assert result_state.task_queue == ["Task A", "Task A.1", "Task B", "Task C"]
            
            # Test end_of_queue position
            agent_action2 = AgentAction(
                tool="create_subtask",
                tool_input={
                    "task_description": "Final cleanup task",
                    "reason": "Need cleanup at the end",
                    "insert_position": "end_of_queue"
                },
                log="Creating subtask at end"
            )
            result_state.agent_outcome = agent_action2
            
            result_state2 = tool_runner(result_state)
            
            # Verify insertion at end
            assert result_state2.task_queue[-1] == "Final cleanup task"