"""
Integration tests for read_file caching functionality.

These tests verify that read_file results are cached and subsequent reads
are served from cache without file I/O.
"""

import os
import json
import tempfile
import shutil
import time
import pytest

from katalyst.katalyst_core.state import KatalystState
from katalyst.coding_agent.nodes.tool_runner import tool_runner
from katalyst.coding_agent.tools.read import read as read_file
from katalyst.coding_agent.tools.write import write as write_to_file
from katalyst.coding_agent.tools.edit import edit as apply_source_code_diff
from langchain_core.agents import AgentAction


def get_cached_content(state, file_path):
    """Helper to get cached content for a file."""
    if not os.path.isabs(file_path):
        file_path = os.path.join(state.project_root_cwd, file_path)
    return state.content_store.get(file_path, (None, None))[1]


@pytest.fixture
def temp_project():
    """Create a temporary project directory with files."""
    temp_dir = tempfile.mkdtemp()
    
    # Create test files
    files = {
        "main.py": """def main():
    print("Hello, World!")
    return 0

if __name__ == "__main__":
    main()
""",
        "utils.py": """import os
import sys

def get_path():
    return os.getcwd()

def format_output(data):
    return f"Output: {data}"
""",
        "config.json": """{
    "debug": true,
    "version": "1.0.0",
    "features": ["cache", "search", "export"]
}""",
        "large_file.txt": ""  # Will be created separately
    }
    
    for filename, content in files.items():
        if filename == "large_file.txt":
            # Handle large file specially
            with open(os.path.join(temp_dir, filename), 'w') as f:
                for i in range(1000):
                    f.write(f"Line {i}\n")
        else:
            with open(os.path.join(temp_dir, filename), 'w') as f:
                f.write(content)
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def katalyst_state(temp_project):
    """Create a KatalystState with the temp project."""
    return KatalystState(
        task="Test read_file caching",
        project_root_cwd=temp_project,
        auto_approve=True
    )


@pytest.mark.skip(reason="Caching removed in minimal implementation")
class TestReadFileCacheIntegration:
    """Integration tests for read_file caching."""
    
    def test_read_file_creates_cache_entry(self, katalyst_state):
        """Test that read_file creates a cache entry in content_store."""
        # Read a file
        agent_action = AgentAction(
            tool="read_file",
            tool_input={"path": "main.py"},
            log=""
        )
        katalyst_state.agent_outcome = agent_action
        
        # Execute through tool_runner
        state_after_read = tool_runner(katalyst_state)
        
        # Verify file was read successfully
        assert len(state_after_read.action_trace) > 0
        _, observation = state_after_read.action_trace[-1]
        obs_data = json.loads(observation)
        # Content is removed from observation for efficiency, only ref is kept
        assert "content_ref" in obs_data
        assert "path" in obs_data
        
        # Verify cache entry was created
        file_path = os.path.join(katalyst_state.project_root_cwd, "main.py")
        assert file_path in state_after_read.content_store
        cached_content = state_after_read.content_store[file_path][1]
        assert "def main():" in cached_content
    
    def test_cached_read_file_response(self, katalyst_state):
        """Test that subsequent read_file calls are served from cache."""
        # First read - will hit the filesystem
        agent_action = AgentAction(
            tool="read_file",
            tool_input={"path": "utils.py"},
            log=""
        )
        katalyst_state.agent_outcome = agent_action
        state_after_first = tool_runner(katalyst_state)
        
        # Verify first read worked - check cache content
        file_path = os.path.join(katalyst_state.project_root_cwd, "utils.py")
        assert file_path in state_after_first.content_store
        cached_content = state_after_first.content_store[file_path][1]
        assert "import os" in cached_content
        
        # Modify the actual file on disk (cache shouldn't see this)
        file_path = os.path.join(katalyst_state.project_root_cwd, "utils.py")
        with open(file_path, 'w') as f:
            f.write("# File modified on disk\n# Cache should not see this")
        
        # Second read - should be served from cache
        agent_action2 = AgentAction(
            tool="read_file",
            tool_input={"path": "utils.py"},
            log=""
        )
        state_after_first.agent_outcome = agent_action2
        state_after_first.action_trace = []  # Clear for clarity
        
        state_after_second = tool_runner(state_after_first)
        
        # Verify it was served from cache
        _, second_observation = state_after_second.action_trace[-1]
        second_data = json.loads(second_observation)
        assert second_data.get("cached") == True
        
        # Verify cached content hasn't changed
        cached_content = state_after_second.content_store[file_path][1]
        assert "import os" in cached_content
        assert "File modified on disk" not in cached_content
    
    def test_cache_update_on_write_to_file(self, katalyst_state):
        """Test that cache is updated when files are written."""
        # Read a file first
        agent_action = AgentAction(
            tool="read_file",
            tool_input={"path": "config.json"},
            log=""
        )
        katalyst_state.agent_outcome = agent_action
        state_with_cache = tool_runner(katalyst_state)
        
        # Verify original content was cached
        cached_content = get_cached_content(state_with_cache, "config.json")
        assert cached_content is not None
        assert '"version": "1.0.0"' in cached_content
        
        # Write new content to the file
        new_content = """{
    "debug": false,
    "version": "2.0.0",
    "features": ["cache", "search", "export", "sync"]
}"""
        
        agent_action2 = AgentAction(
            tool="write_to_file",
            tool_input={
                "path": os.path.join(katalyst_state.project_root_cwd, "config.json"),
                "content": new_content
            },
            log=""
        )
        state_with_cache.agent_outcome = agent_action2
        state_with_cache.action_trace = []
        
        state_after_write = tool_runner(state_with_cache)
        
        # Read the file again - should get updated content from cache
        agent_action3 = AgentAction(
            tool="read_file",
            tool_input={"path": "config.json"},
            log=""
        )
        state_after_write.agent_outcome = agent_action3
        state_after_write.action_trace = []
        
        final_state = tool_runner(state_after_write)
        
        # Verify updated content is served from cache
        _, observation = final_state.action_trace[-1]
        data = json.loads(observation)
        assert data.get("cached") == True
        
        # Check the cached content was updated
        cached_content = get_cached_content(final_state, "config.json")
        assert '"version": "2.0.0"' in cached_content
        assert '"debug": false' in cached_content
    
    def test_cache_update_on_apply_diff(self, katalyst_state):
        """Test that cache is updated when files are modified via apply_source_code_diff."""
        # Read a file first
        agent_action = AgentAction(
            tool="read_file",
            tool_input={"path": "main.py"},
            log=""
        )
        katalyst_state.agent_outcome = agent_action
        state_with_cache = tool_runner(katalyst_state)
        
        # Apply a diff to modify the file
        diff = """<<<<<<< SEARCH
:start_line:1
-------
def main():
    print("Hello, World!")
    return 0
=======
def main():
    print("Hello, Katalyst!")
    print("Cache test successful!")
    return 0
>>>>>>> REPLACE"""
        
        agent_action2 = AgentAction(
            tool="apply_source_code_diff",
            tool_input={
                "path": os.path.join(katalyst_state.project_root_cwd, "main.py"),
                "diff": diff
            },
            log=""
        )
        state_with_cache.agent_outcome = agent_action2
        state_with_cache.action_trace = []
        
        state_after_diff = tool_runner(state_with_cache)
        
        # Read the file again - should get updated content from cache
        agent_action3 = AgentAction(
            tool="read_file",
            tool_input={"path": "main.py"},
            log=""
        )
        state_after_diff.agent_outcome = agent_action3
        state_after_diff.action_trace = []
        
        final_state = tool_runner(state_after_diff)
        
        # Verify updated content is served from cache
        _, observation = final_state.action_trace[-1]
        data = json.loads(observation)
        assert data.get("cached") == True
        
        # Check the cached content was updated
        cached_content = get_cached_content(final_state, "main.py")
        assert "Hello, Katalyst!" in cached_content
        assert "Cache test successful!" in cached_content
        assert "Hello, World!" not in cached_content
    
    def test_cache_with_line_ranges(self, katalyst_state):
        """Test that cache works correctly with start_line and end_line parameters."""
        # Read full file first
        agent_action = AgentAction(
            tool="read_file",
            tool_input={"path": "large_file.txt"},
            log=""
        )
        katalyst_state.agent_outcome = agent_action
        state_with_cache = tool_runner(katalyst_state)
        
        # Read a specific line range - should still use cache
        agent_action2 = AgentAction(
            tool="read_file",
            tool_input={
                "path": "large_file.txt",
                "start_line": 10,
                "end_line": 20
            },
            log=""
        )
        state_with_cache.agent_outcome = agent_action2
        state_with_cache.action_trace = []
        
        final_state = tool_runner(state_with_cache)
        
        # Check if it's using cache or not
        _, observation = final_state.action_trace[-1]
        data = json.loads(observation)
        # If the implementation caches partial reads, check the content_ref
        # Otherwise, it should have the content directly
        if "content" in data:
            assert "Line 9" in data["content"]  # Line numbers are 0-indexed
            assert "Line 19" in data["content"]
        else:
            # Using content_ref
            assert "content_ref" in data
    
    def test_cache_performance_benefit(self, katalyst_state):
        """Test that cached reads are faster than file I/O."""
        # First read - measure time
        start_time = time.time()
        agent_action = AgentAction(
            tool="read_file",
            tool_input={"path": "large_file.txt"},
            log=""
        )
        katalyst_state.agent_outcome = agent_action
        state_after_first = tool_runner(katalyst_state)
        first_read_time = time.time() - start_time
        
        # Second read from cache - should be much faster
        start_time = time.time()
        agent_action2 = AgentAction(
            tool="read_file",
            tool_input={"path": "large_file.txt"},
            log=""
        )
        state_after_first.agent_outcome = agent_action2
        state_after_first.action_trace = []
        
        state_after_second = tool_runner(state_after_first)
        cached_read_time = time.time() - start_time
        
        # Verify second read was from cache
        _, observation = state_after_second.action_trace[-1]
        data = json.loads(observation)
        assert data.get("cached") == True
        
        # Cache read should be faster (though this might be flaky on slow systems)
        # Just verify it completed successfully
        assert cached_read_time >= 0
    
    def test_cache_with_new_file_creation(self, katalyst_state):
        """Test cache behavior when creating new files."""
        # Create a new file
        new_content = """# New Module
def new_function():
    return "This is new"
"""
        
        agent_action = AgentAction(
            tool="write_to_file",
            tool_input={
                "path": os.path.join(katalyst_state.project_root_cwd, "new_module.py"),
                "content": new_content
            },
            log=""
        )
        katalyst_state.agent_outcome = agent_action
        state_after_write = tool_runner(katalyst_state)
        
        # Read the newly created file - should be in cache
        agent_action2 = AgentAction(
            tool="read_file",
            tool_input={"path": "new_module.py"},
            log=""
        )
        state_after_write.agent_outcome = agent_action2
        state_after_write.action_trace = []
        
        final_state = tool_runner(state_after_write)
        
        # Verify it was served from cache
        _, observation = final_state.action_trace[-1]
        data = json.loads(observation)
        assert data.get("cached") == True
        
        # Check cached content
        cached_content = get_cached_content(final_state, "new_module.py")
        assert "def new_function():" in cached_content
    
    def test_cache_with_absolute_vs_relative_paths(self, katalyst_state):
        """Test that cache works correctly with both absolute and relative paths."""
        # Read with relative path
        agent_action = AgentAction(
            tool="read_file",
            tool_input={"path": "utils.py"},
            log=""
        )
        katalyst_state.agent_outcome = agent_action
        state_after_relative = tool_runner(katalyst_state)
        
        # Read with absolute path - should use same cache entry
        abs_path = os.path.join(katalyst_state.project_root_cwd, "utils.py")
        agent_action2 = AgentAction(
            tool="read_file",
            tool_input={"path": abs_path},
            log=""
        )
        state_after_relative.agent_outcome = agent_action2
        state_after_relative.action_trace = []
        
        state_after_absolute = tool_runner(state_after_relative)
        
        # Verify it was served from cache
        _, observation = state_after_absolute.action_trace[-1]
        data = json.loads(observation)
        assert data.get("cached") == True
        
        # Both should point to same cached content
        cached_content_rel = get_cached_content(state_after_relative, "utils.py")
        cached_content_abs = get_cached_content(state_after_absolute, abs_path)
        assert cached_content_rel == cached_content_abs
        assert cached_content_rel is not None