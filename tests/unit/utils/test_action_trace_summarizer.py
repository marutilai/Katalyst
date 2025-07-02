"""
Tests for action trace summarizer.
"""
import pytest

# Skip this entire test file since action_trace is commented out
pytestmark = pytest.mark.skip("action_trace has been commented out in minimal implementation")

from unittest.mock import Mock, patch
from katalyst.katalyst_core.utils.action_trace_summarizer import ActionTraceSummarizer
from langchain_core.agents import AgentAction


class TestActionTraceSummarizer:
    """Test the ActionTraceSummarizer class."""
    
    def test_empty_action_trace(self):
        """Test summarizing an empty action trace."""
        summarizer = ActionTraceSummarizer()
        result = summarizer.summarize_action_trace([])
        assert result == ""
    
    def test_small_action_trace_no_summarization(self):
        """Test that small traces are not summarized."""
        # Create a small action trace
        action1 = AgentAction(tool="read_file", tool_input={"file_path": "test.py"}, log="")
        action2 = AgentAction(tool="write_to_file", tool_input={"file_path": "out.py", "content": "data"}, log="")
        
        action_trace = [
            (action1, "File contents: print('hello')"),
            (action2, "File written successfully")
        ]
        
        summarizer = ActionTraceSummarizer()
        result = summarizer.summarize_action_trace(action_trace, keep_last_n=5, max_chars=5000)
        
        # Should return the formatted trace without summarization
        assert "Previous Action: read_file" in result
        assert "Previous Action: write_to_file" in result
        assert "[PREVIOUS ACTIONS SUMMARY]" not in result
    
    def test_large_action_trace_triggers_summarization(self):
        """Test that large traces trigger summarization."""
        # Create a large action trace (needs to be > 10KB to trigger summarization)
        actions = []
        for i in range(10):
            action = AgentAction(
                tool="read_file", 
                tool_input={"file_path": f"file{i}.py"}, 
                log=""
            )
            observation = f"File {i} contents: " + "x" * 2000  # Larger observation for > 10KB total
            actions.append((action, observation))
        
        summarizer = ActionTraceSummarizer()
        
        # Mock the LLM call for summarization
        with patch.object(summarizer, '_create_summary', return_value="Summary of first 5 actions"):
            result = summarizer.summarize_action_trace(
                actions, 
                keep_last_n=5, 
                max_chars=5000
            )
        
        # Should contain summary and recent actions
        assert "[PREVIOUS ACTIONS SUMMARY]" in result
        assert "Summary of first 5 actions" in result
        assert "Recent actions and observations:" in result
        # Should keep last 5 actions
        assert "file5.py" in result
        assert "file9.py" in result
        # Should not contain early actions in full
        assert "file0.py" not in result
    
    def test_small_trace_no_summary_just_truncate(self):
        """Test that small traces (< 10KB) just get truncated without LLM summarization."""
        # Create a trace under 10KB but over max_chars
        actions = []
        for i in range(8):
            action = AgentAction(
                tool="list_files", 
                tool_input={"path": f"dir{i}"}, 
                log=""
            )
            observation = f"Files in dir{i}: " + "x" * 200
            actions.append((action, observation))
        
        summarizer = ActionTraceSummarizer()
        
        # Should NOT call _create_summary for small traces
        with patch.object(summarizer, '_create_summary') as mock_summary:
            result = summarizer.summarize_action_trace(
                actions, 
                keep_last_n=3, 
                max_chars=1000  # Force it to need compression
            )
            
            # Verify LLM was not called
            mock_summary.assert_not_called()
            
        # Should only contain last 3 actions
        assert "dir5" in result
        assert "dir6" in result
        assert "dir7" in result
        assert "dir0" not in result
        assert "[PREVIOUS ACTIONS SUMMARY]" not in result
    
    def test_format_action_trace(self):
        """Test formatting of action trace."""
        action = AgentAction(
            tool="search_directory", 
            tool_input={"path": "/src", "pattern": "*.py"}, 
            log=""
        )
        observation = "Found 3 files: main.py, utils.py, test.py"
        
        summarizer = ActionTraceSummarizer()
        result = summarizer._format_action_trace([(action, observation)])
        
        assert "Previous Action: search_directory" in result
        assert "Previous Action Input: {'path': '/src', 'pattern': '*.py'}" in result
        assert "Observation: Found 3 files" in result
    
    @patch('katalyst.katalyst_core.utils.action_trace_summarizer.get_llm_client')
    @patch('katalyst.katalyst_core.utils.action_trace_summarizer.get_llm_params')
    def test_create_summary_success(self, mock_get_params, mock_get_client):
        """Test successful summary creation."""
        # Mock LLM response with shorter text that won't be truncated
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Summary"))]
        mock_llm = Mock(return_value=mock_response)
        mock_get_client.return_value = mock_llm
        mock_get_params.return_value = {"temperature": 0.1}
        
        action = AgentAction(tool="read_file", tool_input={"file_path": "test.py"}, log="")
        
        summarizer = ActionTraceSummarizer()
        result = summarizer._create_summary([(action, "File contents")], target_reduction=0.5)
        
        # The summary should be returned (might be truncated if too long)
        assert result == "Summary"
        mock_llm.assert_called_once()
        
    @patch('katalyst.katalyst_core.utils.action_trace_summarizer.get_llm_client')
    @patch('katalyst.katalyst_core.utils.action_trace_summarizer.get_llm_params')
    def test_create_summary_truncates_long_result(self, mock_get_params, mock_get_client):
        """Test that overly long summaries get truncated."""
        # Mock LLM response with very long summary
        long_summary = "x" * 1000
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=long_summary))]
        mock_llm = Mock(return_value=mock_response)
        mock_get_client.return_value = mock_llm
        mock_get_params.return_value = {"temperature": 0.1}
        
        action = AgentAction(tool="read_file", tool_input={"file_path": "test.py"}, log="")
        
        summarizer = ActionTraceSummarizer()
        result = summarizer._create_summary([(action, "Short obs")], target_reduction=0.8)
        
        # Should be truncated to fit target reduction
        assert len(result) < 500  # Much shorter than original
        assert result.endswith("...")
        mock_llm.assert_called_once()
    
    @patch('katalyst.katalyst_core.utils.action_trace_summarizer.get_llm_client')
    @patch('katalyst.katalyst_core.utils.action_trace_summarizer.get_llm_params')
    def test_create_summary_failure(self, mock_get_params, mock_get_client):
        """Test handling of summary creation failure."""
        # Mock LLM to raise exception
        mock_get_client.side_effect = Exception("LLM error")
        mock_get_params.return_value = {"temperature": 0.1}
        
        action = AgentAction(tool="read_file", tool_input={"file_path": "test.py"}, log="")
        
        summarizer = ActionTraceSummarizer()
        result = summarizer._create_summary([(action, "File contents")])
        
        assert result is None
    
    def test_summarization_with_different_components(self):
        """Test summarizer with different LLM components."""
        summarizer = ActionTraceSummarizer(component="planner")
        assert summarizer.component == "planner"
        
        summarizer = ActionTraceSummarizer(component="execution")
        assert summarizer.component == "execution"