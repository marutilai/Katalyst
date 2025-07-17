"""Tests for the summarizer node module."""

import pytest
from unittest.mock import MagicMock, patch, call
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.messages.utils import count_tokens_approximately

from katalyst.coding_agent.nodes.summarizer import (
    get_summarization_node,
    SUMMARIZATION_PROMPT,
)
from katalyst.app.config import (
    MAX_AGGREGATE_TOKENS_IN_SUMMARY_AND_OUTPUT,
    MAX_TOKENS_TO_TRIGGER_SUMMARY,
    MAX_TOKENS_IN_SUMMARY_ONLY,
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
        assert node.max_tokens == MAX_AGGREGATE_TOKENS_IN_SUMMARY_AND_OUTPUT
        assert node.max_tokens_before_summary == MAX_TOKENS_TO_TRIGGER_SUMMARY
        assert node.max_summary_tokens == MAX_TOKENS_IN_SUMMARY_ONLY
        assert node.output_messages_key == "messages"

    @patch("katalyst.coding_agent.nodes.summarizer.get_llm_client")
    def test_summarization_prompt_structure(self, mock_get_llm_client):
        """Test that the summarization prompt is properly structured."""
        mock_get_llm_client.return_value = self.mock_llm
        
        node = get_summarization_node()
        
        # Check that the prompt template has the expected structure
        prompt_template = node.initial_summary_prompt
        messages = prompt_template.messages
        
        assert len(messages) == 2
        assert messages[0].prompt.template == "{messages}"
        assert messages[1].prompt.template == SUMMARIZATION_PROMPT

    @patch("katalyst.coding_agent.nodes.summarizer.get_llm_client")
    def test_summarization_prompt_content(self, mock_get_llm_client):
        """Test that the summarization prompt contains expected content."""
        mock_get_llm_client.return_value = self.mock_llm
        
        # Verify key sections are present in the prompt
        assert "Primary Request and Intent" in SUMMARIZATION_PROMPT
        assert "Key Technical Concepts" in SUMMARIZATION_PROMPT
        assert "Files and Code Sections" in SUMMARIZATION_PROMPT
        assert "Problem Solving" in SUMMARIZATION_PROMPT
        assert "Pending Tasks" in SUMMARIZATION_PROMPT
        assert "Current Work" in SUMMARIZATION_PROMPT
        assert "Optional Next Step" in SUMMARIZATION_PROMPT
        assert "<analysis>" in SUMMARIZATION_PROMPT
        assert "<summary>" in SUMMARIZATION_PROMPT

    @patch("katalyst.coding_agent.nodes.summarizer.get_llm_client")
    def test_multiple_node_instances(self, mock_get_llm_client):
        """Test that multiple instances of the node can be created."""
        mock_get_llm_client.return_value = self.mock_llm
        
        node1 = get_summarization_node()
        node2 = get_summarization_node()
        
        # Should be separate instances
        assert node1 is not node2
        assert mock_get_llm_client.call_count == 2

    @patch("katalyst.coding_agent.nodes.summarizer.get_llm_client")
    def test_node_token_counter_integration(self, mock_get_llm_client):
        """Test that the token counter function is properly integrated."""
        mock_get_llm_client.return_value = self.mock_llm
        
        node = get_summarization_node()
        
        # Test that the token counter is the expected function
        assert callable(node.token_counter)
        assert node.token_counter == count_tokens_approximately
        
        # Test that it works with sample messages
        test_messages = [
            HumanMessage(content="Test message 1"),
            AIMessage(content="Test response 1")
        ]
        
        token_count = node.token_counter(test_messages)
        assert isinstance(token_count, int)
        assert token_count > 0

    @patch("katalyst.coding_agent.nodes.summarizer.get_llm_client")
    def test_summarization_node_type(self, mock_get_llm_client):
        """Test that the correct type of summarization node is returned."""
        mock_get_llm_client.return_value = self.mock_llm
        
        node = get_summarization_node()
        
        # Should be a SummarizationNode from langmem
        assert node.__class__.__name__ == "SummarizationNode"

    def test_prompt_constants_accessibility(self):
        """Test that the prompt constant is accessible and properly formatted."""
        # Test that the prompt is a string
        assert isinstance(SUMMARIZATION_PROMPT, str)
        assert len(SUMMARIZATION_PROMPT) > 0
        
        # Test that it contains the example structure
        assert "<example>" in SUMMARIZATION_PROMPT
        assert "</example>" in SUMMARIZATION_PROMPT
        
        # Test that it has the Reddit reference
        assert "reddit.com" in SUMMARIZATION_PROMPT

    @patch("katalyst.coding_agent.nodes.summarizer.get_llm_client")
    @patch("katalyst.coding_agent.nodes.summarizer.get_logger")
    def test_logger_integration(self, mock_get_logger, mock_get_llm_client):
        """Test that the logger is properly imported and available."""
        mock_get_llm_client.return_value = self.mock_llm
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Import should work without errors
        from katalyst.coding_agent.nodes.summarizer import logger
        
        # Logger should be available
        assert logger is not None
        mock_get_logger.assert_called_once()