"""Integration test for persistent agent implementation."""
import os
import pytest
from unittest.mock import MagicMock, patch
from katalyst.katalyst_core.graph import build_compiled_graph
from katalyst.katalyst_core.state import KatalystState
from langchain_core.messages import AIMessage


@pytest.mark.integration
def test_persistent_agent_flow():
    """Test that the persistent agent maintains conversation state across tasks."""
    # Mock the LangChain models to avoid API calls
    with patch('katalyst.katalyst_core.utils.langchain_models.ChatOpenAI') as mock_openai:
        # Mock the planner model
        mock_planner_model = MagicMock()
        mock_planner_response = MagicMock()
        mock_planner_response.subtasks = [
            "Create a hello.py file",
            "Add a print statement to hello.py"
        ]
        mock_planner_model.with_structured_output.return_value.invoke.return_value = mock_planner_response
        
        # Mock the agent model
        mock_agent_model = MagicMock()
        
        # Configure mock to return different models based on arguments
        def get_mock_model(*args, **kwargs):
            return mock_planner_model if 'planner' in str(kwargs) else mock_agent_model
        
        mock_openai.side_effect = get_mock_model
        
        # Build the graph
        graph = build_compiled_graph()
        
        # Test input
        test_input = {
            "task": "Create a simple hello world file",
            "auto_approve": True,
            "project_root_cwd": "/test",
            "user_input_fn": lambda x: ""
        }
        
        # Mock create_react_agent
        with patch('katalyst.coding_agent.nodes.planner.create_react_agent') as mock_create_agent:
            mock_agent_executor = MagicMock()
            mock_create_agent.return_value = mock_agent_executor
            
            # Simulate agent responses for two tasks
            task1_response = {
                "messages": [
                    AIMessage(content="TASK COMPLETED: Created hello.py file")
                ]
            }
            task2_response = {
                "messages": [
                    AIMessage(content="TASK COMPLETED: Added print statement to hello.py")
                ]
            }
            
            mock_agent_executor.invoke.side_effect = [task1_response, task2_response]
            
            # Run the graph
            result = graph.invoke(test_input)
            
            # Verify the agent was created only once
            mock_create_agent.assert_called_once()
            
            # Verify the agent was invoked twice (once for each task)
            assert mock_agent_executor.invoke.call_count == 2
            
            # Verify state has agent_executor
            assert result.get('agent_executor') is not None
            
            # Verify messages were accumulated
            assert len(result.get('messages', [])) > 0
            
            # Verify both tasks were completed
            assert len(result.get('completed_tasks', [])) == 2


@pytest.mark.integration  
def test_persistent_agent_error_recovery():
    """Test that persistent agent handles errors without recreating the agent."""
    with patch('katalyst.katalyst_core.utils.langchain_models.ChatOpenAI') as mock_openai:
        # Mock models
        mock_model = MagicMock()
        mock_openai.return_value = mock_model
        
        # Mock planner response
        mock_planner_response = MagicMock()
        mock_planner_response.subtasks = ["Task that will fail"]
        mock_model.with_structured_output.return_value.invoke.return_value = mock_planner_response
        
        # Build graph
        graph = build_compiled_graph()
        
        # Test input
        test_input = {
            "task": "Test error handling",
            "auto_approve": True,
            "project_root_cwd": "/test",
            "user_input_fn": lambda x: ""
        }
        
        with patch('katalyst.coding_agent.nodes.planner.create_react_agent') as mock_create_agent:
            mock_agent_executor = MagicMock()
            mock_create_agent.return_value = mock_agent_executor
            
            # Simulate agent error
            mock_agent_executor.invoke.side_effect = Exception("Test error")
            
            # Run should handle error gracefully
            result = graph.invoke(test_input)
            
            # Verify agent was created only once despite error
            mock_create_agent.assert_called_once()
            
            # Verify error was captured
            assert result.get('error_message') is not None