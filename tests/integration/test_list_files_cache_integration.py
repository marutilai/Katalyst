"""
Integration tests for list_files caching functionality.

These tests verify the caching behavior with actual filesystem operations
and real tool execution through the graph.
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
import pytest

from katalyst.katalyst_core.state import KatalystState
from katalyst.coding_agent.nodes.tool_runner import tool_runner
from katalyst.coding_agent.tools.list_files import list_files
from katalyst.coding_agent.tools.write_to_file import write_to_file
from katalyst.coding_agent.tools.execute_command import execute_command
from katalyst.katalyst_core.utils.directory_cache import DirectoryCache
from langchain_core.agents import AgentAction


@pytest.fixture
def temp_project():
    """Create a temporary project directory with structure."""
    temp_dir = tempfile.mkdtemp()
    
    # Create a realistic project structure
    structure = {
        "src": {
            "main.py": "def main():\n    print('Hello')",
            "utils": {
                "__init__.py": "",
                "helper.py": "def help():\n    pass",
                "config.py": "DEBUG = True"
            },
            "models": {
                "__init__.py": "",
                "user.py": "class User:\n    pass",
                "product.py": "class Product:\n    pass"
            }
        },
        "tests": {
            "__init__.py": "",
            "test_main.py": "def test_main():\n    pass",
            "test_utils.py": "def test_utils():\n    pass"
        },
        "docs": {
            "README.md": "# Documentation",
            "api": {
                "index.md": "# API Docs",
                "reference.md": "# Reference"
            }
        },
        "README.md": "# Test Project",
        "setup.py": "from setuptools import setup",
        ".gitignore": "*.pyc\n__pycache__/\n.env"
    }
    
    def create_structure(base_path, structure):
        for name, content in structure.items():
            path = os.path.join(base_path, name)
            if isinstance(content, dict):
                os.makedirs(path, exist_ok=True)
                create_structure(path, content)
            else:
                with open(path, 'w') as f:
                    f.write(content)
    
    create_structure(temp_dir, structure)
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def katalyst_state(temp_project):
    """Create a KatalystState with the temp project."""
    return KatalystState(
        task="Test list_files caching",
        project_root_cwd=temp_project,
        auto_approve=True
    )


class TestListFilesCacheIntegration:
    """Integration tests for list_files caching."""
    
    def test_first_call_triggers_full_scan_and_cache(self, katalyst_state):
        """Test that the first list_files call triggers a full scan and subsequent calls use cache."""
        # First call - should trigger full scan
        agent_action = AgentAction(
            tool="list_files",
            tool_input={"path": "src", "recursive": False},
            log=""
        )
        katalyst_state.agent_outcome = agent_action
        
        # Execute through tool_runner
        state_after_first = tool_runner(katalyst_state)
        
        # Verify cache was initialized
        assert state_after_first.directory_cache is not None
        cache = DirectoryCache.from_dict(state_after_first.directory_cache)
        assert cache.full_scan_done
        
        # Verify the response
        assert len(state_after_first.action_trace) > 0
        _, first_observation = state_after_first.action_trace[-1]
        first_data = json.loads(first_observation)
        
        # Should have the src directory contents
        assert "main.py" in first_data["files"]
        assert "utils/" in first_data["files"]
        assert "models/" in first_data["files"]
        
        # Second call - should use cache
        agent_action2 = AgentAction(
            tool="list_files",
            tool_input={"path": "src/utils", "recursive": False},
            log=""
        )
        state_after_first.agent_outcome = agent_action2
        state_after_first.action_trace = []  # Clear for clarity
        
        # Execute again
        state_after_second = tool_runner(state_after_first)
        
        # Verify it was served from cache
        _, second_observation = state_after_second.action_trace[-1]
        second_data = json.loads(second_observation)
        
        assert second_data.get("cached") == True
        assert "__init__.py" in second_data["files"]
        assert "helper.py" in second_data["files"]
        assert "config.py" in second_data["files"]
    
    def test_recursive_listing_from_cache(self, katalyst_state):
        """Test that recursive listings work correctly from cache."""
        # Initialize cache with first call
        agent_action = AgentAction(
            tool="list_files",
            tool_input={"path": ".", "recursive": False},
            log=""
        )
        katalyst_state.agent_outcome = agent_action
        state_with_cache = tool_runner(katalyst_state)
        
        # Now request recursive listing from cache
        agent_action2 = AgentAction(
            tool="list_files",
            tool_input={"path": "src", "recursive": True},
            log=""
        )
        state_with_cache.agent_outcome = agent_action2
        state_with_cache.action_trace = []
        
        final_state = tool_runner(state_with_cache)
        
        # Check recursive listing
        _, observation = final_state.action_trace[-1]
        data = json.loads(observation)
        
        assert data.get("cached") == True
        # Should include nested files
        assert "main.py" in data["files"]
        assert "utils/" in data["files"]
        assert "utils/helper.py" in data["files"]
        assert "utils/config.py" in data["files"]
        assert "models/" in data["files"]
        assert "models/user.py" in data["files"]
    
    def test_cache_update_on_file_creation(self, katalyst_state):
        """Test that cache is updated when new files are created."""
        # Initialize cache
        agent_action = AgentAction(
            tool="list_files",
            tool_input={"path": ".", "recursive": False},
            log=""
        )
        katalyst_state.agent_outcome = agent_action
        state_with_cache = tool_runner(katalyst_state)
        
        # Create a new file
        new_file_path = os.path.join(katalyst_state.project_root_cwd, "src", "new_module.py")
        agent_action2 = AgentAction(
            tool="write_to_file",
            tool_input={
                "path": new_file_path,
                "content": "# New module\nprint('New')"
            },
            log=""
        )
        state_with_cache.agent_outcome = agent_action2
        state_with_cache.action_trace = []
        
        state_after_write = tool_runner(state_with_cache)
        
        # List src directory again - should include new file
        agent_action3 = AgentAction(
            tool="list_files",
            tool_input={"path": "src", "recursive": False},
            log=""
        )
        state_after_write.agent_outcome = agent_action3
        state_after_write.action_trace = []
        
        final_state = tool_runner(state_after_write)
        
        # Verify new file is in cache
        _, observation = final_state.action_trace[-1]
        data = json.loads(observation)
        
        assert data.get("cached") == True
        assert "new_module.py" in data["files"]
    
    def test_cache_update_on_nested_file_creation(self, katalyst_state):
        """Test cache updates when creating files in new directories."""
        # Initialize cache
        agent_action = AgentAction(
            tool="list_files",
            tool_input={"path": ".", "recursive": False},
            log=""
        )
        katalyst_state.agent_outcome = agent_action
        state_with_cache = tool_runner(katalyst_state)
        
        # Create a file in a new nested directory
        new_file_path = os.path.join(
            katalyst_state.project_root_cwd, 
            "src", "components", "ui", "button.py"
        )
        agent_action2 = AgentAction(
            tool="write_to_file",
            tool_input={
                "path": new_file_path,
                "content": "class Button:\n    pass"
            },
            log=""
        )
        state_with_cache.agent_outcome = agent_action2
        state_with_cache.action_trace = []
        
        state_after_write = tool_runner(state_with_cache)
        
        # List src directory - should show new components directory
        agent_action3 = AgentAction(
            tool="list_files",
            tool_input={"path": "src", "recursive": False},
            log=""
        )
        state_after_write.agent_outcome = agent_action3
        state_after_write.action_trace = []
        
        state_after_list = tool_runner(state_after_write)
        
        _, observation = state_after_list.action_trace[-1]
        data = json.loads(observation)
        assert "components/" in data["files"]
        
        # List the new components directory
        agent_action4 = AgentAction(
            tool="list_files",
            tool_input={"path": "src/components", "recursive": True},
            log=""
        )
        state_after_list.agent_outcome = agent_action4
        state_after_list.action_trace = []
        
        final_state = tool_runner(state_after_list)
        
        _, observation = final_state.action_trace[-1]
        data = json.loads(observation)
        assert data.get("cached") == True
        # When listing recursively, we get the file path directly
        assert "ui/button.py" in data["files"]
    
    def test_cache_invalidation_on_execute_command(self, katalyst_state):
        """Test that execute_command invalidates the cache."""
        # Initialize cache
        agent_action = AgentAction(
            tool="list_files",
            tool_input={"path": ".", "recursive": False},
            log=""
        )
        katalyst_state.agent_outcome = agent_action
        state_with_cache = tool_runner(katalyst_state)
        
        # Verify cache exists
        assert state_with_cache.directory_cache is not None
        cache_before = DirectoryCache.from_dict(state_with_cache.directory_cache)
        assert cache_before.full_scan_done
        
        # Execute a command
        agent_action2 = AgentAction(
            tool="execute_command",
            tool_input={"command": "echo 'test'"},
            log=""
        )
        state_with_cache.agent_outcome = agent_action2
        state_with_cache.action_trace = []
        
        state_after_command = tool_runner(state_with_cache)
        
        # Check cache was invalidated
        cache_after = DirectoryCache.from_dict(state_after_command.directory_cache)
        assert not cache_after.full_scan_done
        assert len(cache_after.cache) == 0
        
        # Next list_files should trigger new scan
        agent_action3 = AgentAction(
            tool="list_files",
            tool_input={"path": "src", "recursive": False},
            log=""
        )
        state_after_command.agent_outcome = agent_action3
        state_after_command.action_trace = []
        
        final_state = tool_runner(state_after_command)
        
        # Should have rescanned
        cache_final = DirectoryCache.from_dict(final_state.directory_cache)
        assert cache_final.full_scan_done
    
    def test_cache_consistency_with_gitignore(self, katalyst_state):
        """Test that cache respects .gitignore rules."""
        # Create some files that should be ignored
        pycache_dir = os.path.join(katalyst_state.project_root_cwd, "src", "__pycache__")
        os.makedirs(pycache_dir, exist_ok=True)
        with open(os.path.join(pycache_dir, "main.cpython-39.pyc"), "wb") as f:
            f.write(b"compiled python")
        
        env_file = os.path.join(katalyst_state.project_root_cwd, ".env")
        with open(env_file, "w") as f:
            f.write("SECRET_KEY=secret")
        
        # Initialize cache
        agent_action = AgentAction(
            tool="list_files",
            tool_input={"path": ".", "recursive": False},
            log=""
        )
        katalyst_state.agent_outcome = agent_action
        state_with_cache = tool_runner(katalyst_state)
        
        # List root directory
        _, observation = state_with_cache.action_trace[-1]
        data = json.loads(observation)
        
        # .env should be ignored per .gitignore
        assert ".env" not in data["files"]
        
        # List src directory recursively
        agent_action2 = AgentAction(
            tool="list_files",
            tool_input={"path": "src", "recursive": True},
            log=""
        )
        state_with_cache.agent_outcome = agent_action2
        state_with_cache.action_trace = []
        
        final_state = tool_runner(state_with_cache)
        
        _, observation = final_state.action_trace[-1]
        data = json.loads(observation)
        
        # __pycache__ should be ignored
        assert "__pycache__/" not in data["files"]
        assert all("__pycache__" not in f for f in data["files"])
    
    def test_cache_performance_benefit(self, katalyst_state):
        """Test that cached operations don't increment inner_cycles."""
        # Initialize cache
        agent_action = AgentAction(
            tool="list_files",
            tool_input={"path": ".", "recursive": False},
            log=""
        )
        katalyst_state.agent_outcome = agent_action
        initial_cycles = katalyst_state.inner_cycles
        
        state_with_cache = tool_runner(katalyst_state)
        cycles_after_first = state_with_cache.inner_cycles
        
        # First call should not increment cycles (tool_runner doesn't increment)
        assert cycles_after_first == initial_cycles
        
        # Make 5 more list_files calls from cache
        current_state = state_with_cache
        for i in range(5):
            agent_action = AgentAction(
                tool="list_files",
                tool_input={"path": f".", "recursive": False},
                log=""
            )
            current_state.agent_outcome = agent_action
            current_state.action_trace = []  # Clear to avoid bloat
            current_state = tool_runner(current_state)
        
        # Inner cycles should still be the same (cache hits don't increment)
        assert current_state.inner_cycles == initial_cycles
        
        # Verify all were cache hits
        cache = DirectoryCache.from_dict(current_state.directory_cache)
        assert cache.full_scan_done
    
    def test_edge_cases(self, katalyst_state):
        """Test edge cases like empty directories, special characters, etc."""
        # Create empty directory
        empty_dir = os.path.join(katalyst_state.project_root_cwd, "empty_dir")
        os.makedirs(empty_dir)
        
        # Create directory with special characters
        special_dir = os.path.join(katalyst_state.project_root_cwd, "test-dir_2024")
        os.makedirs(special_dir)
        with open(os.path.join(special_dir, "file with spaces.txt"), "w") as f:
            f.write("content")
        
        # Initialize cache
        agent_action = AgentAction(
            tool="list_files",
            tool_input={"path": ".", "recursive": False},
            log=""
        )
        katalyst_state.agent_outcome = agent_action
        state_with_cache = tool_runner(katalyst_state)
        
        # List empty directory
        agent_action2 = AgentAction(
            tool="list_files",
            tool_input={"path": "empty_dir", "recursive": True},
            log=""
        )
        state_with_cache.agent_outcome = agent_action2
        state_with_cache.action_trace = []
        
        state_after_empty = tool_runner(state_with_cache)
        
        _, observation = state_after_empty.action_trace[-1]
        data = json.loads(observation)
        assert data["files"] == []
        assert data.get("cached") == True
        
        # List directory with special characters
        agent_action3 = AgentAction(
            tool="list_files",
            tool_input={"path": "test-dir_2024", "recursive": False},
            log=""
        )
        state_after_empty.agent_outcome = agent_action3
        state_after_empty.action_trace = []
        
        final_state = tool_runner(state_after_empty)
        
        _, observation = final_state.action_trace[-1]
        data = json.loads(observation)
        assert "file with spaces.txt" in data["files"]
        assert data.get("cached") == True