"""Test chat history compression in state."""
import pytest
from unittest.mock import Mock, patch
from katalyst.katalyst_core.state import KatalystState
from katalyst.coding_agent.nodes.agent_react import agent_react
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


def create_large_chat_history(state: KatalystState, count: int):
    """Add many messages to chat history."""
    for i in range(count):
        state.chat_history.append(HumanMessage(content=f"User message {i}"))
        state.chat_history.append(AIMessage(content=f"Assistant response {i}"))


@pytest.mark.skip(reason="Chat history compression removed in minimal implementation")
def test_chat_history_compression():
    """Test that chat history is compressed in state when threshold is exceeded."""
    # Create state with many messages
    state = KatalystState(
        project_root_cwd="/test",
        task="Test chat compression",
        task_queue=["Test chat compression"],
        task_idx=0,
        original_plan=["Test chat compression"]
    )
    
    # Add 60 messages (30 pairs) - should trigger compression at >50
    create_large_chat_history(state, 30)
    
    initial_count = len(state.chat_history)
    assert initial_count == 60
    
    # Mock the LLM response
    mock_response = Mock()
    mock_response.thought = "Testing chat compression"
    mock_response.action = "list_files"
    mock_response.action_input = {"path": "/"}
    
    with patch('katalyst.coding_agent.nodes.agent_react.get_llm_client') as mock_get_llm:
        mock_llm = Mock()
        mock_llm.chat.completions.create.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        
        # Mock the conversation summarizer to avoid real LLM calls
        with patch('katalyst.katalyst_core.utils.conversation_summarizer.ConversationSummarizer._create_summary') as mock_create_summary:
            mock_create_summary.return_value = "This is a summary of the previous conversation about testing"
            
            # Run agent_react which should trigger compression
            state = agent_react(state)
    
    # Check compressed state
    compressed_count = len(state.chat_history)
    
    # Should be compressed (summary + kept messages + new messages from agent_react)
    assert compressed_count < initial_count
    assert compressed_count <= 13  # 1 summary + 10 kept + 2 new from agent_react
    
    # Check for summary message
    has_summary = any(
        "[CONVERSATION SUMMARY]" in msg.content 
        for msg in state.chat_history 
        if isinstance(msg, AIMessage)
    )
    assert has_summary, "Should have a conversation summary in compressed history"
    
    print(f"Chat history compression: {initial_count} -> {compressed_count} messages")


@pytest.mark.skip(reason="Chat history compression removed in minimal implementation")
def test_chat_history_no_compression_under_threshold():
    """Test that chat history is not compressed when under threshold."""
    state = KatalystState(
        project_root_cwd="/test",
        task="Test no compression",
        task_queue=["Test no compression"],
        task_idx=0,
        original_plan=["Test no compression"]
    )
    
    # Add only 20 messages (under threshold of 50)
    create_large_chat_history(state, 10)
    
    initial_count = len(state.chat_history)
    assert initial_count == 20
    
    # Mock the LLM response
    mock_response = Mock()
    mock_response.thought = "Testing no compression"
    mock_response.final_answer = "Done"
    mock_response.action = None
    mock_response.action_input = None
    
    with patch('katalyst.coding_agent.nodes.agent_react.get_llm_client') as mock_get_llm:
        mock_llm = Mock()
        mock_llm.chat.completions.create.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        
        state = agent_react(state)
    
    # Should not compress (added 1 message from agent_react - just the thought)
    # When agent goes directly to final answer, only thought is added, not action
    assert len(state.chat_history) == initial_count + 1
    
    # Should not have summary
    has_summary = any(
        "[CONVERSATION SUMMARY]" in msg.content 
        for msg in state.chat_history
    )
    assert not has_summary, "Should not have a summary when under threshold"


if __name__ == "__main__":
    test_chat_history_compression()
    test_chat_history_no_compression_under_threshold()
    print("All tests passed!")