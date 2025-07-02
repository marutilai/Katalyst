"""
Unit tests for list_files caching functionality.
"""

import os
import json
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
import pytest
import inspect

from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.directory_cache import DirectoryCache
from katalyst.coding_agent.nodes.tool_runner import tool_runner
from langchain_core.agents import AgentAction


@pytest.fixture
def temp_project_dir():
    """Create a temporary directory structure for testing."""
    temp_dir = tempfile.mkdtemp()
    
    # Create test directory structure
    os.makedirs(os.path.join(temp_dir, "src", "utils"))
    os.makedirs(os.path.join(temp_dir, "tests"))
    os.makedirs(os.path.join(temp_dir, "docs"))
    
    # Create test files
    with open(os.path.join(temp_dir, "README.md"), "w") as f:
        f.write("# Test Project")
    
    with open(os.path.join(temp_dir, "src", "main.py"), "w") as f:
        f.write("print('hello')")
    
    with open(os.path.join(temp_dir, "src", "utils", "helper.py"), "w") as f:
        f.write("def help(): pass")
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_state(temp_project_dir):
    """Create a mock KatalystState for testing."""
    state = KatalystState(
        task="Test task",
        project_root_cwd=temp_project_dir,
        auto_approve=True
    )
    return state


class TestDirectoryCache:
    """Test DirectoryCache functionality."""
    
    def test_directory_cache_initialization(self, temp_project_dir):
        """Test cache initialization."""
        cache = DirectoryCache(temp_project_dir)
        assert cache.root_path == os.path.abspath(temp_project_dir)
        assert not cache.full_scan_done
        assert len(cache.cache) == 0
    
    def test_full_scan(self, temp_project_dir):
        """Test full directory scan."""
        cache = DirectoryCache(temp_project_dir)
        cache.perform_full_scan(respect_gitignore=False)
        
        assert cache.full_scan_done
        assert len(cache.cache) > 0
        
        # Check root directory
        root_entries = cache.cache[cache.root_path]
        assert "src/" in root_entries
        assert "tests/" in root_entries
        assert "docs/" in root_entries
        assert "README.md" in root_entries
        
        # Check src directory
        src_path = os.path.join(cache.root_path, "src")
        src_entries = cache.cache[src_path]
        assert "utils/" in src_entries
        assert "main.py" in src_entries
    
    def test_get_listing_non_recursive(self, temp_project_dir):
        """Test getting non-recursive directory listing from cache."""
        cache = DirectoryCache(temp_project_dir)
        cache.perform_full_scan(respect_gitignore=False)
        
        # Get root listing
        root_files = cache.get_listing(temp_project_dir, recursive=False)
        assert "src/" in root_files
        assert "README.md" in root_files
        assert "src/main.py" not in root_files  # Non-recursive
        
        # Get src listing
        src_path = os.path.join(temp_project_dir, "src")
        src_files = cache.get_listing(src_path, recursive=False)
        assert "utils/" in src_files
        assert "main.py" in src_files
        assert "utils/helper.py" not in src_files  # Non-recursive
    
    def test_get_listing_recursive(self, temp_project_dir):
        """Test getting recursive directory listing from cache."""
        cache = DirectoryCache(temp_project_dir)
        cache.perform_full_scan(respect_gitignore=False)
        
        # Get recursive listing from root
        all_files = cache.get_listing(temp_project_dir, recursive=True)
        assert "src/" in all_files
        assert "src/main.py" in all_files
        assert "src/utils/" in all_files
        assert "src/utils/helper.py" in all_files
        assert "README.md" in all_files
        
        # Get recursive listing from src
        src_path = os.path.join(temp_project_dir, "src")
        src_files = cache.get_listing(src_path, recursive=True)
        assert "main.py" in src_files
        assert "utils/" in src_files
        assert "utils/helper.py" in src_files
    
    def test_update_for_file_operation(self, temp_project_dir):
        """Test cache updates for file operations."""
        cache = DirectoryCache(temp_project_dir)
        cache.perform_full_scan(respect_gitignore=False)
        
        # Test file creation
        new_file = os.path.join(temp_project_dir, "new_file.txt")
        cache.update_for_file_operation(new_file, "created")
        
        root_entries = cache.cache[cache.root_path]
        assert "new_file.txt" in root_entries
        
        # Test file deletion
        cache.update_for_file_operation(new_file, "deleted")
        root_entries = cache.cache[cache.root_path]
        assert "new_file.txt" not in root_entries
    
    def test_update_for_directory_creation(self, temp_project_dir):
        """Test cache updates for directory creation."""
        cache = DirectoryCache(temp_project_dir)
        cache.perform_full_scan(respect_gitignore=False)
        
        # Create new directory in cache
        new_dir = os.path.join(temp_project_dir, "new_dir")
        cache.update_for_directory_creation(new_dir)
        
        # Check parent directory updated
        root_entries = cache.cache[cache.root_path]
        assert "new_dir/" in root_entries
        
        # Check new directory exists in cache
        assert new_dir in cache.cache
        assert cache.cache[new_dir] == []
    
    def test_cache_invalidation(self, temp_project_dir):
        """Test cache invalidation."""
        cache = DirectoryCache(temp_project_dir)
        cache.perform_full_scan(respect_gitignore=False)
        
        assert cache.full_scan_done
        assert len(cache.cache) > 0
        
        cache.invalidate()
        
        assert not cache.full_scan_done
        assert len(cache.cache) == 0
    
    def test_serialization(self, temp_project_dir):
        """Test cache serialization and deserialization."""
        cache = DirectoryCache(temp_project_dir)
        cache.perform_full_scan(respect_gitignore=False)
        
        # Serialize
        cache_dict = cache.to_dict()
        assert isinstance(cache_dict, dict)
        assert cache_dict["full_scan_done"]
        assert len(cache_dict["cache"]) > 0
        
        # Deserialize
        new_cache = DirectoryCache.from_dict(cache_dict)
        assert new_cache.full_scan_done
        assert new_cache.root_path == cache.root_path
        assert new_cache.cache == cache.cache


@pytest.mark.skip(reason="Directory caching removed in minimal implementation")
class TestListFilesCaching:
    """Test list_files caching integration in tool_runner."""
    
    @patch('katalyst.coding_agent.nodes.tool_runner.inspect.signature')
    @patch('katalyst.coding_agent.nodes.tool_runner.REGISTERED_TOOL_FUNCTIONS_MAP')
    def test_first_list_files_triggers_full_scan(self, mock_tools, mock_signature, mock_state):
        """Test that first list_files call triggers a full scan."""
        # Mock list_files tool with proper __code__ attribute
        mock_list_files = Mock(return_value=json.dumps({
            "path": mock_state.project_root_cwd,
            "files": ["file1.txt", "dir1/"]
        }))
        # Mock the __code__ attribute for _prepare_tool_input
        mock_list_files.__code__ = Mock()
        mock_list_files.__code__.co_varnames = []
        mock_tools.get.return_value = mock_list_files
        
        # Mock inspect.signature to return empty parameters
        mock_sig = Mock()
        mock_sig.parameters = {}
        mock_signature.return_value = mock_sig
        
        # Set up agent action for list_files
        agent_action = AgentAction(
            tool="list_files",
            tool_input={"path": ".", "recursive": False},
            log=""
        )
        mock_state.agent_outcome = agent_action
        
        # Execute tool_runner
        result_state = tool_runner(mock_state)
        
        # Check that directory cache was initialized
        assert result_state.directory_cache is not None
        
        # Check that list_files was called with root path and recursive=True for full scan
        call_args = mock_list_files.call_args[1]
        # Internal params like _first_call are filtered out before calling the tool
        assert call_args["path"] == mock_state.project_root_cwd
        assert call_args["recursive"] == True
        
        # Verify cache was populated
        cache = DirectoryCache.from_dict(result_state.directory_cache)
        assert cache.full_scan_done
    
    @patch('katalyst.coding_agent.nodes.tool_runner.REGISTERED_TOOL_FUNCTIONS_MAP')
    def test_cached_list_files_response(self, mock_tools, mock_state):
        """Test that subsequent list_files calls are served from cache."""
        # Initialize cache with test data
        cache = DirectoryCache(mock_state.project_root_cwd)
        cache.cache[mock_state.project_root_cwd] = ["file1.txt", "dir1/"]
        cache.full_scan_done = True
        mock_state.directory_cache = cache.to_dict()
        
        # Set up agent action for list_files
        agent_action = AgentAction(
            tool="list_files",
            tool_input={"path": mock_state.project_root_cwd, "recursive": False},
            log=""
        )
        mock_state.agent_outcome = agent_action
        
        # Execute tool_runner
        result_state = tool_runner(mock_state)
        
        # Check that the tool was NOT called (served from cache)
        mock_tools.get.assert_not_called()
        
        # Check action trace contains cached response
        assert len(result_state.action_trace) > 0
        _, observation = result_state.action_trace[-1]
        obs_data = json.loads(observation)
        assert obs_data["cached"] == True
        assert obs_data["files"] == ["file1.txt", "dir1/"]
    
    @patch('katalyst.coding_agent.nodes.tool_runner.REGISTERED_TOOL_FUNCTIONS_MAP')
    def test_execute_command_invalidates_cache(self, mock_tools, mock_state):
        """Test that execute_command invalidates the directory cache."""
        # Initialize cache
        cache = DirectoryCache(mock_state.project_root_cwd)
        cache.full_scan_done = True
        cache.cache["test"] = ["file.txt"]
        mock_state.directory_cache = cache.to_dict()
        
        # Mock execute_command tool
        mock_execute = Mock(return_value=json.dumps({
            "success": True,
            "output": "command output"
        }))
        mock_execute.__code__ = Mock()
        mock_execute.__code__.co_varnames = []
        mock_tools.get.return_value = mock_execute
        
        # Set up agent action for execute_command
        agent_action = AgentAction(
            tool="execute_command",
            tool_input={"command": "rm test.txt"},
            log=""
        )
        mock_state.agent_outcome = agent_action
        
        # Execute tool_runner
        result_state = tool_runner(mock_state)
        
        # Check that cache was invalidated
        cache_after = DirectoryCache.from_dict(result_state.directory_cache)
        assert not cache_after.full_scan_done
        assert len(cache_after.cache) == 0
    
    @patch('katalyst.coding_agent.nodes.tool_runner.REGISTERED_TOOL_FUNCTIONS_MAP')
    def test_write_to_file_updates_cache(self, mock_tools, mock_state):
        """Test that write_to_file updates the directory cache."""
        # Initialize cache
        cache = DirectoryCache(mock_state.project_root_cwd)
        cache.cache[mock_state.project_root_cwd] = ["existing.txt"]
        cache.full_scan_done = True
        mock_state.directory_cache = cache.to_dict()
        
        # Mock write_to_file tool
        new_file_path = os.path.join(mock_state.project_root_cwd, "new_file.txt")
        mock_write = Mock(return_value=json.dumps({
            "success": True,
            "path": new_file_path,
            "created": True
        }))
        mock_write.__code__ = Mock()
        mock_write.__code__.co_varnames = ["auto_approve"]  # write_to_file accepts auto_approve
        mock_tools.get.return_value = mock_write
        
        # Set up agent action for write_to_file
        agent_action = AgentAction(
            tool="write_to_file",
            tool_input={"path": new_file_path, "content": "test content"},
            log=""
        )
        mock_state.agent_outcome = agent_action
        
        # Execute tool_runner
        result_state = tool_runner(mock_state)
        
        # Check that cache was updated
        cache_after = DirectoryCache.from_dict(result_state.directory_cache)
        root_entries = cache_after.cache[mock_state.project_root_cwd]
        assert "new_file.txt" in root_entries