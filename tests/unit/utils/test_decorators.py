"""
Unit tests for decorators module
"""
import os
import pytest

# Skip this entire test file since decorators use chat_history which has been commented out
pytestmark = pytest.mark.skip("decorators use chat_history which has been commented out")

from unittest.mock import MagicMock, patch
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.decorators import compress_chat_history


# pytestmark = pytest.mark.unit


class TestCompressChatHistoryDecorator:
    """Test the compress_chat_history decorator."""
    
    @pytest.fixture
    def mock_state(self):
        """Create a mock state with chat history."""
        state = MagicMock(spec=KatalystState)
        state.chat_history = []
        state.task = "Test task"
        state.project_root_cwd = "/test/path"
        return state
    
    def test_decorator_with_short_history(self, mock_state):
        """Test that decorator doesn't compress when history is short."""
        # Add a few messages (under threshold)
        mock_state.chat_history = [
            SystemMessage(content="System prompt"),
            HumanMessage(content="User message 1"),
            AIMessage(content="Assistant response 1"),
        ]
        
        @compress_chat_history()
        def test_node(state):
            return state
        
        # Call the decorated function
        result = test_node(mock_state)
        
        # History should be unchanged
        assert len(result.chat_history) == 3
        assert isinstance(result.chat_history[0], SystemMessage)
    
    @patch('katalyst.katalyst_core.utils.decorators.ConversationSummarizer')
    def test_decorator_with_long_history(self, mock_summarizer_class, mock_state):
        """Test that decorator compresses when history exceeds threshold."""
        # Create a long history (55 messages)
        messages = [SystemMessage(content="System prompt")]
        for i in range(54):
            messages.append(HumanMessage(content=f"User message {i}"))
            
        mock_state.chat_history = messages
        
        # Mock the summarizer
        mock_summarizer = MagicMock()
        mock_summarizer_class.return_value = mock_summarizer
        
        # Mock compressed output (system + summary + last 10)
        compressed = [
            {"role": "system", "content": "System prompt"},
            {"role": "assistant", "content": "[CONVERSATION SUMMARY]\nSummary here\n[END OF SUMMARY]"},
        ]
        # Add last 10 messages
        for i in range(44, 54):
            compressed.append({"role": "user", "content": f"User message {i}"})
            
        mock_summarizer.summarize_conversation.return_value = compressed
        
        @compress_chat_history()
        def test_node(state):
            return state
        
        # Call the decorated function
        result = test_node(mock_state)
        
        # Verify compression was called
        mock_summarizer.summarize_conversation.assert_called_once()
        call_args = mock_summarizer.summarize_conversation.call_args
        assert call_args[1]['keep_last_n'] == 10
        
        # Verify history was updated
        assert len(result.chat_history) == 12  # system + summary + 10 recent
        assert isinstance(result.chat_history[0], SystemMessage)
        assert isinstance(result.chat_history[1], AIMessage)
        assert "[CONVERSATION SUMMARY]" in result.chat_history[1].content
    
    def test_decorator_with_custom_thresholds(self, mock_state):
        """Test decorator with custom trigger and keep_last_n values."""
        # Add exactly 31 messages
        messages = []
        for i in range(31):
            messages.append(HumanMessage(content=f"Message {i}"))
        mock_state.chat_history = messages
        
        @compress_chat_history(trigger=30, keep_last_n=5)
        def test_node(state):
            return state
        
        with patch('katalyst.katalyst_core.utils.decorators.ConversationSummarizer') as mock_summarizer_class:
            mock_summarizer = MagicMock()
            mock_summarizer_class.return_value = mock_summarizer
            
            # Return compressed messages
            compressed = [{"role": "assistant", "content": "Summary"}]
            for i in range(26, 31):
                compressed.append({"role": "user", "content": f"Message {i}"})
            mock_summarizer.summarize_conversation.return_value = compressed
            
            # Call the decorated function
            result = test_node(mock_state)
            
            # Verify custom keep_last_n was used
            call_args = mock_summarizer.summarize_conversation.call_args
            assert call_args[1]['keep_last_n'] == 5
    
    def test_decorator_with_env_vars(self, mock_state, monkeypatch):
        """Test that decorator reads from environment variables."""
        # Set environment variables
        monkeypatch.setenv("KATALYST_CHAT_SUMMARY_TRIGGER", "25")
        monkeypatch.setenv("KATALYST_CHAT_SUMMARY_KEEP_LAST_N", "7")
        
        # Add 26 messages (over env var threshold)
        messages = []
        for i in range(26):
            messages.append(HumanMessage(content=f"Message {i}"))
        mock_state.chat_history = messages
        
        @compress_chat_history()
        def test_node(state):
            return state
        
        with patch('katalyst.katalyst_core.utils.decorators.ConversationSummarizer') as mock_summarizer_class:
            mock_summarizer = MagicMock()
            mock_summarizer_class.return_value = mock_summarizer
            
            # Return compressed messages
            compressed = []
            for i in range(19, 26):
                compressed.append({"role": "user", "content": f"Message {i}"})
            mock_summarizer.summarize_conversation.return_value = compressed
            
            # Call the decorated function
            result = test_node(mock_state)
            
            # Verify env var keep_last_n was used
            call_args = mock_summarizer.summarize_conversation.call_args
            assert call_args[1]['keep_last_n'] == 7
    
    def test_decorator_handles_tool_messages(self, mock_state):
        """Test that decorator properly handles ToolMessage objects."""
        # Create history with tool messages
        mock_state.chat_history = [
            SystemMessage(content="System"),
            HumanMessage(content="User request"),
            AIMessage(content="I'll use a tool"),
            ToolMessage(content="Tool result", name="test_tool", tool_call_id="test_id"),
        ] * 15  # 60 messages total
        
        @compress_chat_history()
        def test_node(state):
            return state
        
        with patch('katalyst.katalyst_core.utils.decorators.ConversationSummarizer') as mock_summarizer_class:
            mock_summarizer = MagicMock()
            mock_summarizer_class.return_value = mock_summarizer
            
            # Just return something to avoid errors
            mock_summarizer.summarize_conversation.return_value = [
                {"role": "system", "content": "System"},
                {"role": "assistant", "content": "Summary"},
            ]
            
            # Call the decorated function
            result = test_node(mock_state)
            
            # Verify tool messages were converted properly
            call_args = mock_summarizer.summarize_conversation.call_args
            messages = call_args[0][0]
            
            # Find a tool message conversion
            tool_message_found = False
            for msg in messages:
                if msg.get('role') == 'user' and 'Tool Result (test_tool)' in msg.get('content', ''):
                    tool_message_found = True
                    break
            
            assert tool_message_found, "Tool messages should be converted to user messages with proper format"
    
    def test_decorator_preserves_function_attributes(self):
        """Test that decorator preserves the original function's attributes."""
        @compress_chat_history()
        def test_node(state):
            """Test node docstring."""
            return state
        
        # Check that function attributes are preserved
        assert test_node.__name__ == "test_node"
        assert test_node.__doc__ == "Test node docstring."
    
    def test_decorator_logs_compression_stats(self, mock_state, caplog):
        """Test that decorator logs compression statistics."""
        # Create long history
        messages = []
        for i in range(60):
            messages.append(HumanMessage(content=f"Message {i}"))
        mock_state.chat_history = messages
        
        @compress_chat_history()
        def test_node(state):
            return state
        
        with patch('katalyst.katalyst_core.utils.decorators.ConversationSummarizer') as mock_summarizer_class:
            mock_summarizer = MagicMock()
            mock_summarizer_class.return_value = mock_summarizer
            
            # Return much shorter list
            compressed = [
                {"role": "assistant", "content": "Summary"},
                {"role": "user", "content": "Recent message"},
            ]
            mock_summarizer.summarize_conversation.return_value = compressed
            
            # Call with logging
            result = test_node(mock_state)
            
            # Check logs
            assert any("[CHAT_COMPRESSION]" in record.message and "60 messages > 50 trigger" in record.message 
                      for record in caplog.records)
            assert any("[CHAT_COMPRESSION]" in record.message and "reduction" in record.message 
                      for record in caplog.records)