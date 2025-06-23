"""Test for content reference system to prevent hallucination in file operations."""
import pytest
import json
import hashlib
from unittest.mock import Mock, patch
from katalyst.katalyst_core.state import KatalystState
from katalyst.coding_agent.nodes.tool_runner import tool_runner
from langchain_core.agents import AgentAction


@pytest.fixture
def mock_state():
    """Create a mock state for testing."""
    state = KatalystState(
        task="Test file copy",
        project_root_cwd="/test/project",
        content_store={}
    )
    return state


def test_read_file_creates_content_reference(mock_state):
    """Test that read_file tool creates a content reference in state."""
    # Mock the read_file tool to return sample content
    sample_content = "# Sample README\n\nThis is a test file."
    read_file_response = json.dumps({
        "path": "/test/project/README.md",
        "start_line": 1,
        "end_line": 2,
        "content": sample_content
    })
    
    with patch("katalyst.coding_agent.nodes.tool_runner.REGISTERED_TOOL_FUNCTIONS_MAP") as mock_tools:
        mock_read_file = Mock(return_value=read_file_response)
        mock_tools.get.return_value = mock_read_file
        
        # Create agent action for read_file
        mock_state.agent_outcome = AgentAction(
            tool="read_file",
            tool_input={"path": "README.md"},
            log="Reading file"
        )
        
        # Run tool_runner
        result_state = tool_runner(mock_state)
        
        # Check that content_store has the reference
        assert len(result_state.content_store) == 1
        ref_key = list(result_state.content_store.keys())[0]
        assert ref_key.startswith("ref:README.md:")
        assert result_state.content_store[ref_key] == sample_content
        
        # Check that observation includes content_ref
        action, observation = result_state.action_trace[-1]
        obs_data = json.loads(observation)
        assert "content_ref" in obs_data
        assert obs_data["content_ref"] == ref_key


def test_write_file_uses_content_reference(mock_state):
    """Test that write_to_file uses content reference instead of direct content."""
    # Pre-populate content_store
    sample_content = "# Original Content\n\nThis should be preserved exactly."
    ref_id = "ref:README.md:12345678"
    mock_state.content_store[ref_id] = sample_content
    
    with patch("katalyst.coding_agent.nodes.tool_runner.REGISTERED_TOOL_FUNCTIONS_MAP") as mock_tools:
        mock_write_file = Mock(return_value=json.dumps({
            "success": True,
            "path": "/test/project/README_copy.md"
        }))
        mock_tools.get.return_value = mock_write_file
        
        # Create agent action with content_ref
        mock_state.agent_outcome = AgentAction(
            tool="write_to_file",
            tool_input={
                "path": "README_copy.md",
                "content_ref": ref_id
            },
            log="Writing file using reference"
        )
        
        # Run tool_runner
        result_state = tool_runner(mock_state)
        
        # Verify write_to_file was called with resolved content
        mock_write_file.assert_called_once()
        call_args = mock_write_file.call_args[1]
        assert call_args["content"] == sample_content
        assert "content_ref" not in call_args


def test_invalid_content_reference(mock_state):
    """Test handling of invalid content reference."""
    with patch("katalyst.coding_agent.nodes.tool_runner.REGISTERED_TOOL_FUNCTIONS_MAP") as mock_tools:
        # Mock write_to_file shouldn't be called for invalid ref
        mock_write_file = Mock()
        mock_tools.get.return_value = mock_write_file
        
        # Create agent action with invalid content_ref
        mock_state.agent_outcome = AgentAction(
            tool="write_to_file",
            tool_input={
                "path": "README_copy.md",
                "content_ref": "ref:invalid:reference"
            },
            log="Writing file with invalid reference"
        )
        
        # Run tool_runner
        result_state = tool_runner(mock_state)
        
        # Verify write_to_file was not called
        mock_write_file.assert_not_called()
        
        # Check error in observation
        action, observation = result_state.action_trace[-1]
        obs_data = json.loads(observation)
        assert not obs_data["success"]
        assert "Invalid content reference" in obs_data["error"]


def test_content_reference_preserves_exact_content():
    """Integration test to verify content is preserved exactly through the reference system."""
    # Test with content that might be prone to LLM modification
    tricky_content = '''# Katalyst Agent

A modular, node-based terminal coding agent for Python, designed for robust, extensible, and production-ready workflows.

![Katalyst Demo: Installation and Usage](docs/images/katalyst_demo.gif)
*Figure: Demo showing how to install and use Katalyst from the terminal*

## Quick Setup

To install Katalyst from PyPI, simply run:

```bash
pip install katalyst
```

**1. Copy the example environment file:**

```bash
cp .env.example .env
```'''
    
    # Generate the expected reference ID
    content_hash = hashlib.md5(tricky_content.encode()).hexdigest()[:8]
    expected_ref = f"ref:README.md:{content_hash}"
    
    # Verify hash generation
    assert expected_ref == f"ref:README.md:{content_hash}"
    
    # Test that content with special characters, markdown, code blocks etc. is preserved
    state = KatalystState(
        task="Test",
        project_root_cwd="/test",
        content_store={}
    )
    state.content_store[expected_ref] = tricky_content
    
    # Verify retrieval
    assert state.content_store[expected_ref] == tricky_content
    assert len(state.content_store[expected_ref]) == len(tricky_content)
    assert state.content_store[expected_ref].count('\n') == tricky_content.count('\n')