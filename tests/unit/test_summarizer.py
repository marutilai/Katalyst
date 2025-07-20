"""Tests for the summarizer node module."""

import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.messages.utils import count_tokens_approximately

from katalyst.coding_agent.nodes.summarizer import (
    get_summarization_node,
    SUMMARIZATION_PROMPT,
)
from katalyst.app.config import (
    MAX_AGGREGATE_TOKENS,
    MAX_TOKENS_BEFORE_SUMMARY,
    MAX_SUMMARY_TOKENS,
)


class TestSummarizationNode:
    """Test the summarization node functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm = MagicMock()
        self.mock_llm.invoke.return_value = MagicMock(content="Test summary")

    @patch("katalyst.coding_agent.nodes.summarizer.get_llm_client")
    def test_get_summarization_node_creation(self, mock_get_llm_client):
        """Test that get_summarization_node creates a properly configured node."""
        mock_get_llm_client.return_value = self.mock_llm
        
        node = get_summarization_node()
        
        # Verify the LLM client was requested for summarizer
        mock_get_llm_client.assert_called_once_with("summarizer")
        
        # Verify the node is properly configured
        assert node.token_counter == count_tokens_approximately
        assert node.model == self.mock_llm
        assert node.max_tokens == MAX_AGGREGATE_TOKENS
        assert node.max_tokens_before_summary == MAX_TOKENS_BEFORE_SUMMARY
        assert node.max_summary_tokens == MAX_SUMMARY_TOKENS
        assert node.output_messages_key == "messages"

    @patch("katalyst.coding_agent.nodes.summarizer.get_llm_client")
    def test_summarization_prompt_structure(self, mock_get_llm_client):
        """Test that the summarization prompt is properly structured."""
        mock_get_llm_client.return_value = self.mock_llm
        
        node = get_summarization_node()
        
        # Check prompt template exists and has expected structure
        prompt_template = node.initial_summary_prompt
        assert prompt_template is not None
        
        # Verify prompt contains key sections
        assert "User's Request" in SUMMARIZATION_PROMPT
        assert "Completed Work" in SUMMARIZATION_PROMPT
        assert "Technical Context" in SUMMARIZATION_PROMPT
        assert "Current Status" in SUMMARIZATION_PROMPT
        assert "Next Steps" in SUMMARIZATION_PROMPT

    @patch("katalyst.coding_agent.nodes.summarizer.get_llm_client")
    def test_summarization_node_with_messages(self, mock_get_llm_client):
        """Test summarization node processes messages correctly."""
        mock_get_llm_client.return_value = self.mock_llm
        
        node = get_summarization_node()
        
        # Create test messages
        messages = [
            HumanMessage(content="Create a TODO app"),
            AIMessage(content="I'll help you create a TODO app."),
            HumanMessage(content="Add user authentication"),
            AIMessage(content="I'll add authentication to the TODO app.")
        ]
        
        # Verify node can process messages
        # Note: We're not testing the actual summarization behavior
        # as that's handled by LangMem internally
        assert node.output_messages_key == "messages"
        assert node.token_counter is not None

    @patch("katalyst.coding_agent.nodes.summarizer.get_llm_client")
    @patch("katalyst.coding_agent.nodes.summarizer.logger")
    def test_debug_logging(self, mock_logger, mock_get_llm_client):
        """Test that debug logging includes threshold information."""
        mock_get_llm_client.return_value = self.mock_llm
        
        node = get_summarization_node()
        
        # Verify debug log was called with threshold info
        mock_logger.debug.assert_called_once()
        log_message = mock_logger.debug.call_args[0][0]
        assert "trigger=" in log_message
        assert "max=" in log_message
        assert "summary_budget=" in log_message
        assert str(MAX_TOKENS_BEFORE_SUMMARY) in log_message
        assert str(MAX_AGGREGATE_TOKENS) in log_message
        assert str(MAX_SUMMARY_TOKENS) in log_message

    def test_configuration_constants(self):
        """Test that configuration constants have sensible values."""
        # Verify thresholds make sense
        assert MAX_AGGREGATE_TOKENS > MAX_TOKENS_BEFORE_SUMMARY
        assert MAX_SUMMARY_TOKENS < MAX_TOKENS_BEFORE_SUMMARY
        assert MAX_AGGREGATE_TOKENS == 50000  # 50k
        assert MAX_TOKENS_BEFORE_SUMMARY == 40000  # 40k
        assert MAX_SUMMARY_TOKENS == 8000  # 8k