"""
Unit tests for conversation summarizer
"""
import pytest

# Skip this entire test file since conversation_summarizer uses llms service which has been removed
pytestmark = pytest.mark.skip("conversation_summarizer uses llms service which has been removed")

from unittest.mock import MagicMock, patch
from katalyst.katalyst_core.utils._conversation_summarizer import ConversationSummarizer


# pytestmark = pytest.mark.unit


class TestConversationSummarizer:
    """Test the ConversationSummarizer class."""
    
    def test_initialization_default(self):
        """Test initialization with default component."""
        summarizer = ConversationSummarizer()
        assert summarizer.component == "execution"
    
    def test_initialization_custom_component(self):
        """Test initialization with custom component."""
        summarizer = ConversationSummarizer(component="planner")
        assert summarizer.component == "planner"
    
    def test_summarize_conversation_empty(self):
        """Test summarization with empty messages."""
        summarizer = ConversationSummarizer()
        result = summarizer.summarize_conversation([])
        assert result == []
    
    def test_summarize_conversation_short(self):
        """Test when conversation is shorter than keep_last_n."""
        summarizer = ConversationSummarizer()
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        result = summarizer.summarize_conversation(messages, keep_last_n=5)
        assert result == messages  # Should return unchanged
    
    @patch('katalyst.katalyst_core.utils.conversation_summarizer.get_llm_client')
    @patch('katalyst.katalyst_core.utils.conversation_summarizer.get_llm_params')
    def test_summarize_conversation_long(self, mock_llm_params, mock_llm_client):
        """Test summarization of long conversation."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """Context: The current state to continue from.
1. Original Request: Help with Python file operations
2. Completed Tasks: Created reader.py with read_file function that handles basic file reading
3. Current Project State: reader.py exists with working read_file function using context managers
4. What Does NOT Exist Yet: Error handling for large files not implemented
5. Technical Setup: Python with standard library file I/O
6. Next Task Context: Need to add error handling for large files"""
        
        mock_llm = MagicMock()
        mock_llm.return_value = mock_response
        mock_llm_client.return_value = mock_llm
        mock_llm_params.return_value = {"model": "test-model", "timeout": 30}
        
        summarizer = ConversationSummarizer()
        
        # Create a long conversation
        messages = [
            {"role": "system", "content": "You are a coding assistant"},
            {"role": "user", "content": "Help me with Python file operations"},
            {"role": "assistant", "content": "I'll help you with file operations"},
            {"role": "user", "content": "I need to read a file"},
            {"role": "assistant", "content": "Let me create a file reader"},
            {"role": "user", "content": "Make it handle errors"},
            {"role": "assistant", "content": "Added error handling"},
            {"role": "user", "content": "What about large files?"},
            {"role": "assistant", "content": "Working on that next"}
        ]
        
        result = summarizer.summarize_conversation(messages, keep_last_n=2)
        
        # Should have: system message + summary + last 2 messages
        assert len(result) == 4
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "assistant"  # Summary is assistant message
        assert "[CONVERSATION SUMMARY]" in result[1]["content"]
        assert "Context:" in result[1]["content"]
        assert result[2]["role"] == "user"  # "What about large files?"
        assert result[3]["role"] == "assistant"  # "Working on that next"
    
    def test_summarize_text_empty(self):
        """Test text summarization with empty text."""
        summarizer = ConversationSummarizer()
        assert summarizer.summarize_text("") == ""
        assert summarizer.summarize_text("   ") == "   "
    
    @patch('katalyst.katalyst_core.utils.conversation_summarizer.get_llm_client')
    @patch('katalyst.katalyst_core.utils.conversation_summarizer.get_llm_params')
    def test_summarize_text_with_context(self, mock_llm_params, mock_llm_client):
        """Test text summarization with context."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Summary: File contains user authentication logic with JWT tokens"
        
        mock_llm = MagicMock()
        mock_llm.return_value = mock_response
        mock_llm_client.return_value = mock_llm
        mock_llm_params.return_value = {"model": "test-model", "timeout": 30}
        
        summarizer = ConversationSummarizer()
        
        long_text = "def authenticate_user():\n    # lots of code here" * 50
        result = summarizer.summarize_text(long_text, context="auth.py file content")
        
        assert "authentication logic" in result
        assert len(result) < len(long_text)
    
    @patch('katalyst.katalyst_core.utils.conversation_summarizer.get_llm_client')
    def test_summarize_conversation_llm_error(self, mock_llm_client):
        """Test handling of LLM errors during conversation summarization."""
        mock_llm_client.side_effect = Exception("LLM API Error")
        
        summarizer = ConversationSummarizer()
        
        messages = [
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "Message 2"},
            {"role": "assistant", "content": "Response 2"},
            {"role": "user", "content": "Message 3"},
            {"role": "assistant", "content": "Response 3"}
        ]
        
        # Should return original messages on error
        result = summarizer.summarize_conversation(messages, keep_last_n=2)
        assert result == messages
    
    @patch('katalyst.katalyst_core.utils.conversation_summarizer.get_llm_client')
    def test_summarize_text_llm_error(self, mock_llm_client):
        """Test handling of LLM errors during text summarization."""
        mock_llm_client.side_effect = Exception("LLM API Error")
        
        summarizer = ConversationSummarizer()
        
        long_text = "This is a very long text " * 100
        result = summarizer.summarize_text(long_text)
        
        # Should return truncated text on error
        assert result.endswith("... [truncated due to error]")
        assert len(result) <= 1030  # 1000 chars + truncation message
    
    def test_system_messages_preserved(self):
        """Test that system messages are always preserved."""
        summarizer = ConversationSummarizer()
        
        messages = [
            {"role": "system", "content": "System prompt 1"},
            {"role": "system", "content": "System prompt 2"},
            {"role": "user", "content": "User message"},
            {"role": "assistant", "content": "Assistant response"}
        ]
        
        # Even with keep_last_n=0, system messages should be preserved
        with patch('katalyst.katalyst_core.utils.conversation_summarizer.get_llm_client'):
            result = summarizer.summarize_conversation(messages, keep_last_n=0)
            
            system_messages = [msg for msg in result if msg["role"] == "system"]
            assert len(system_messages) == 2
            assert system_messages[0]["content"] == "System prompt 1"
            assert system_messages[1]["content"] == "System prompt 2"
    
    @patch('katalyst.katalyst_core.utils.conversation_summarizer.get_llm_client')
    @patch('katalyst.katalyst_core.utils.conversation_summarizer.get_llm_params')
    def test_summary_prompt_structure(self, mock_llm_params, mock_llm_client):
        """Test that the summary prompt includes all required sections."""
        prompt_captured = None
        
        def capture_prompt(messages, **kwargs):
            nonlocal prompt_captured
            prompt_captured = messages[0]["content"]
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Test summary"
            return mock_response
        
        mock_llm = MagicMock(side_effect=capture_prompt)
        mock_llm_client.return_value = mock_llm
        mock_llm_params.return_value = {}
        
        summarizer = ConversationSummarizer()
        messages = [
            {"role": "user", "content": "Test message"},
            {"role": "assistant", "content": "Test response"}
        ]
        
        summarizer._create_summary(messages)
        
        # Verify prompt structure
        assert prompt_captured is not None
        assert "RESULT-FOCUSED" in prompt_captured
        assert "Original Request:" in prompt_captured
        assert "Completed Tasks:" in prompt_captured
        assert "Current Project State:" in prompt_captured
        assert "What Does NOT Exist Yet:" in prompt_captured
        assert "Technical Setup:" in prompt_captured
        assert "Next Task Context:" in prompt_captured
    
    def test_compression_stats_logging(self, caplog):
        """Test that compression statistics are logged."""
        with patch('katalyst.katalyst_core.utils.conversation_summarizer.get_llm_client') as mock_llm:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Short summary"
            
            mock_llm_instance = MagicMock()
            mock_llm_instance.return_value = mock_response
            mock_llm.return_value = mock_llm_instance
            
            summarizer = ConversationSummarizer()
            
            messages = [
                {"role": "user", "content": "A" * 1000},
                {"role": "assistant", "content": "B" * 1000},
                {"role": "user", "content": "C" * 100}
            ]
            
            summarizer.summarize_conversation(messages, keep_last_n=1)
            
            # Check that compression stats were logged
            assert any("Compressed" in record.message and "reduction" in record.message 
                      for record in caplog.records)