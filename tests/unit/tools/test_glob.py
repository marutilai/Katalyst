"""Unit tests for the glob tool"""

import pytest
import json
import os
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path
from katalyst.coding_agent.tools.glob import glob
os.environ['KATALYST_LOG_LEVEL'] = 'ERROR'  # Disable debug logging for tests


class TestGlobTool:
    """Test cases for the glob tool"""

    @patch('katalyst.coding_agent.tools.glob.should_ignore_path')
    @patch('katalyst.coding_agent.tools.glob.Path')
    @patch('katalyst.coding_agent.tools.glob.os.path.exists')
    def test_glob_simple_pattern(self, mock_exists, mock_path_class, mock_should_ignore):
        """Test simple glob pattern matching"""
        mock_exists.return_value = True
        mock_should_ignore.return_value = False
        
        # Mock Path and its methods
        mock_base_path = Mock()
        mock_base_path.resolve.return_value = mock_base_path
        mock_base_path.__str__ = Mock(return_value="/test/dir")
        
        # Create mock file paths
        mock_file1 = Mock()
        mock_file1.is_dir.return_value = False
        mock_file1.relative_to.return_value = Path("test.py")
        
        mock_file2 = Mock()
        mock_file2.is_dir.return_value = False
        mock_file2.relative_to.return_value = Path("main.py")
        
        mock_base_path.glob.return_value = [mock_file1, mock_file2]
        mock_path_class.return_value = mock_base_path
        
        result = glob("*.py")
        result_dict = json.loads(result)
        
        assert "files" in result_dict
        assert len(result_dict["files"]) == 2
        assert "main.py" in result_dict["files"]  # Should be sorted
        assert "test.py" in result_dict["files"]
        assert result_dict["pattern"] == "*.py"

    @patch('katalyst.coding_agent.tools.glob.should_ignore_path')
    @patch('katalyst.coding_agent.tools.glob.Path')
    @patch('katalyst.coding_agent.tools.glob.os.path.exists')
    def test_glob_recursive_pattern(self, mock_exists, mock_path_class, mock_should_ignore):
        """Test recursive glob pattern"""
        mock_exists.return_value = True
        mock_should_ignore.return_value = False
        
        mock_base_path = Mock()
        mock_base_path.resolve.return_value = mock_base_path
        mock_base_path.__str__ = Mock(return_value="/test/dir")
        
        # Create mock nested files
        mock_file1 = Mock()
        mock_file1.is_dir.return_value = False
        mock_file1.relative_to.return_value = Path("src/main.py")
        
        mock_file2 = Mock()
        mock_file2.is_dir.return_value = False
        mock_file2.relative_to.return_value = Path("tests/test_main.py")
        
        # Since "**/*.py" starts with **/, it uses rglob with pattern "*.py"
        mock_base_path.rglob.return_value = [mock_file1, mock_file2]
        mock_path_class.return_value = mock_base_path
        
        result = glob("**/*.py")
        result_dict = json.loads(result)
        
        assert len(result_dict["files"]) == 2
        assert "src/main.py" in result_dict["files"]
        assert "tests/test_main.py" in result_dict["files"]

    def test_glob_no_pattern(self):
        """Test error when no pattern provided"""
        result = glob("")
        result_dict = json.loads(result)
        
        assert "error" in result_dict
        assert "No pattern provided" in result_dict["error"]

    @patch('katalyst.coding_agent.tools.glob.os.path.exists')
    def test_glob_path_not_found(self, mock_exists):
        """Test error when base path doesn't exist"""
        mock_exists.return_value = False
        
        result = glob("*.py", path="/nonexistent")
        result_dict = json.loads(result)
        
        assert "error" in result_dict
        assert "Base path not found" in result_dict["error"]

    @patch('katalyst.coding_agent.tools.glob.should_ignore_path')
    @patch('katalyst.coding_agent.tools.glob.Path')
    @patch('katalyst.coding_agent.tools.glob.os.path.exists')
    def test_glob_no_matches(self, mock_exists, mock_path_class, mock_should_ignore):
        """Test when no files match the pattern"""
        mock_exists.return_value = True
        
        mock_base_path = Mock()
        mock_base_path.resolve.return_value = mock_base_path
        mock_base_path.__str__ = Mock(return_value="/test/dir")
        mock_base_path.glob.return_value = []
        mock_path_class.return_value = mock_base_path
        
        result = glob("*.xyz")
        result_dict = json.loads(result)
        
        assert result_dict["files"] == []
        assert "info" in result_dict
        assert "No files found" in result_dict["info"]

    @patch('katalyst.coding_agent.tools.glob.should_ignore_path')
    @patch('katalyst.coding_agent.tools.glob.Path')
    @patch('katalyst.coding_agent.tools.glob.os.path.exists')
    def test_glob_respects_gitignore(self, mock_exists, mock_path_class, mock_should_ignore):
        """Test that glob respects gitignore by default"""
        mock_exists.return_value = True
        
        mock_base_path = Mock()
        mock_base_path.resolve.return_value = mock_base_path
        mock_base_path.__str__ = Mock(return_value="/test/dir")
        
        # Create files where one is gitignored
        mock_file1 = Mock()
        mock_file1.is_dir.return_value = False
        mock_file1.relative_to.return_value = Path("allowed.py")
        
        mock_file2 = Mock()
        mock_file2.is_dir.return_value = False
        mock_file2.relative_to.return_value = Path("ignored.py")
        
        mock_base_path.glob.return_value = [mock_file1, mock_file2]
        mock_path_class.return_value = mock_base_path
        
        # Mock should_ignore_path to ignore the second file
        mock_should_ignore.side_effect = lambda path, base, respect: "ignored" in path
        
        result = glob("*.py")
        result_dict = json.loads(result)
        
        assert len(result_dict["files"]) == 1
        assert "allowed.py" in result_dict["files"]
        assert "ignored.py" not in result_dict["files"]

    @patch('katalyst.coding_agent.tools.glob.should_ignore_path')
    @patch('katalyst.coding_agent.tools.glob.Path')
    @patch('katalyst.coding_agent.tools.glob.os.path.exists')
    def test_glob_ignore_directories(self, mock_exists, mock_path_class, mock_should_ignore):
        """Test that directories are ignored unless pattern ends with /"""
        mock_exists.return_value = True
        mock_should_ignore.return_value = False
        
        mock_base_path = Mock()
        mock_base_path.resolve.return_value = mock_base_path
        mock_base_path.__str__ = Mock(return_value="/test/dir")
        
        # Create a mix of files and directories
        mock_file = Mock()
        mock_file.is_dir.return_value = False
        mock_file.relative_to.return_value = Path("file.txt")
        
        mock_dir = Mock()
        mock_dir.is_dir.return_value = True
        mock_dir.relative_to.return_value = Path("subdir")
        
        mock_base_path.glob.return_value = [mock_file, mock_dir]
        mock_path_class.return_value = mock_base_path
        
        result = glob("*")
        result_dict = json.loads(result)
        
        assert len(result_dict["files"]) == 1
        assert "file.txt" in result_dict["files"]
        assert "subdir" not in result_dict["files"]

    @patch('katalyst.coding_agent.tools.glob.should_ignore_path')
    @patch('katalyst.coding_agent.tools.glob.Path')
    @patch('katalyst.coding_agent.tools.glob.os.path.exists')
    def test_glob_truncate_results(self, mock_exists, mock_path_class, mock_should_ignore):
        """Test that results are truncated at max_results"""
        mock_exists.return_value = True
        mock_should_ignore.return_value = False
        
        mock_base_path = Mock()
        mock_base_path.resolve.return_value = mock_base_path
        mock_base_path.__str__ = Mock(return_value="/test/dir")
        
        # Create 150 mock files
        mock_files = []
        for i in range(150):
            mock_file = Mock()
            mock_file.is_dir.return_value = False
            mock_file.relative_to.return_value = Path(f"file{i:03d}.txt")
            mock_files.append(mock_file)
        
        mock_base_path.glob.return_value = mock_files
        mock_path_class.return_value = mock_base_path
        
        result = glob("*.txt")
        result_dict = json.loads(result)
        
        assert len(result_dict["files"]) == 100  # max_results
        assert "info" in result_dict
        assert "truncated" in result_dict["info"].lower()

    @patch('katalyst.coding_agent.tools.glob.should_ignore_path')
    @patch('katalyst.coding_agent.tools.glob.Path')
    @patch('katalyst.coding_agent.tools.glob.os.path.exists')
    def test_glob_error_handling(self, mock_exists, mock_path_class, mock_should_ignore):
        """Test error handling for glob exceptions"""
        mock_exists.return_value = True
        
        # Create a mock that raises an exception when glob is called
        mock_base_path = Mock()
        mock_base_path.resolve.return_value = mock_base_path
        mock_base_path.__str__ = Mock(return_value="/test/dir")
        mock_base_path.glob.side_effect = Exception("Glob error")
        mock_path_class.return_value = mock_base_path
        
        result = glob("*.py")
        result_dict = json.loads(result)
        
        assert "error" in result_dict
        assert "Error processing glob pattern" in result_dict["error"]