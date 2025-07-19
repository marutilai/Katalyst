#!/usr/bin/env python3
"""Integration test to verify action trace compression actually reduces state size."""

import pytest
from unittest.mock import Mock, patch
from katalyst.katalyst_core.state import KatalystState
from katalyst.coding_agent.nodes.executor import executor
from langchain_core.agents import AgentAction, AgentFinish
import json


def create_large_action_trace(state: KatalystState, count: int):
    """Add many actions with large observations to the trace."""
    for i in range(count):
        action = AgentAction(
            tool="read_file",
            tool_input={"path": f"/file{i}.py"},
            log=f"Reading file {i}"
        )
        
        # Simulate a large observation (1KB each)
        large_content = "x" * 1000
        observation = json.dumps({
            "path": f"/file{i}.py",
            "content": large_content,
            "content_ref": f"/file{i}.py",
            "success": True
        }, indent=2)
        
        state.action_trace.append((action, observation))


@pytest.mark.skip(reason="Action trace compression removed in minimal implementation")
def test_action_trace_compression_reduces_state_size():
    """Test that action trace compression actually reduces the stored state size."""
    # Create initial state
    state = KatalystState(
        project_root_cwd="/test",
        task="Test compression",
        task_queue=["Test compression"],
        task_idx=0,
        original_plan=["Test compression"]
    )
    
    # Add 12 large actions (should trigger compression at >10)
    create_large_action_trace(state, 12)
    
    # Check initial size
    initial_entries = len(state.action_trace)
    initial_size = sum(len(str(action)) + len(obs) for action, obs in state.action_trace)
    
    assert initial_entries == 12
    assert initial_size > 12000  # Each entry is ~1KB
    
    # Mock the LLM response to return a simple action
    mock_response = Mock()
    mock_response.thought = "Testing compression"
    mock_response.action = "list_files"
    mock_response.action_input = {"path": "/"}
    
    # Mock the LLM client
    with patch('katalyst.coding_agent.nodes.executor.get_llm_client') as mock_get_llm:
        mock_llm = Mock()
        mock_llm.chat.completions.create.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        
        # Mock the action trace summarizer to avoid real LLM calls
        with patch('katalyst.katalyst_core.utils.action_trace_summarizer.ActionTraceSummarizer._create_summary') as mock_create_summary:
            mock_create_summary.return_value = "Summary of first 7 actions: Read multiple files"
            
            # Run executor which should trigger compression
            state = executor(state)
    
    # Check compressed size
    compressed_entries = len(state.action_trace)
    compressed_size = sum(len(str(action)) + len(obs) for action, obs in state.action_trace)
    
    # Should have fewer entries (summary + kept recent ones)
    assert compressed_entries < initial_entries
    assert compressed_entries <= 6  # 1 summary + 5 recent
    
    # Should be much smaller
    assert compressed_size < initial_size * 0.5  # At least 50% reduction
    
    # Check that we have a summary entry
    has_summary = any(action.tool == "[SUMMARY]" for action, _ in state.action_trace)
    assert has_summary, "Should have a summary entry in the compressed trace"
    
    print(f"Compression results:")
    print(f"  Entries: {initial_entries} -> {compressed_entries}")
    print(f"  Size: {initial_size} -> {compressed_size} ({(1-compressed_size/initial_size)*100:.1f}% reduction)")


@pytest.mark.skip(reason="Action trace compression removed in minimal implementation")
def test_action_trace_no_compression_under_threshold():
    """Test that action trace is not compressed when under threshold."""
    state = KatalystState(
        project_root_cwd="/test",
        task="Test no compression",
        task_queue=["Test no compression"],
        task_idx=0,
        original_plan=["Test no compression"]
    )
    
    # Add only 5 actions (under threshold of 10)
    create_large_action_trace(state, 5)
    
    initial_entries = len(state.action_trace)
    
    # Mock the LLM response
    mock_response = Mock()
    mock_response.thought = "Testing no compression"
    mock_response.action = "list_files"
    mock_response.action_input = {"path": "/"}
    
    with patch('katalyst.coding_agent.nodes.executor.get_llm_client') as mock_get_llm:
        mock_llm = Mock()
        mock_llm.chat.completions.create.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        
        state = executor(state)
    
    # Should not compress
    assert len(state.action_trace) == initial_entries
    
    # Should not have summary
    has_summary = any(action.tool == "[SUMMARY]" for action, _ in state.action_trace)
    assert not has_summary, "Should not have a summary entry when under threshold"


if __name__ == "__main__":
    test_action_trace_compression_reduces_state_size()
    test_action_trace_no_compression_under_threshold()
    print("All tests passed!")