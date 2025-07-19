"""Unit tests for the read tool"""

import pytest
import json
from unittest.mock import patch, mock_open, MagicMock, Mock
from katalyst.coding_agent.tools.read import read
import os
os.environ['KATALYST_LOG_LEVEL'] = 'ERROR'  # Disable debug logging for tests


class TestReadTool:
    """Test cases for the read tool"""

    @patch('katalyst.coding_agent.tools.read.open', new_callable=mock_open, read_data='Hello World\nLine 2\nLine 3')
    @patch('katalyst.coding_agent.tools.read.os.path.isfile')
    @patch('katalyst.coding_agent.tools.read.os.path.exists')
    def test_read_entire_file(self, mock_exists, mock_isfile, mock_file):
        """Test reading entire file content"""
        mock_exists.return_value = True
        mock_isfile.return_value = True
        
        result = read("test.txt")
        result_dict = json.loads(result)
        
        assert "content" in result_dict
        assert result_dict["content"] == "Hello World\nLine 2\nLine 3"
        assert result_dict["path"] == "test.txt"
        mock_file.assert_called_with("test.txt", "r", encoding="utf-8")

    @patch('katalyst.coding_agent.tools.read.open', new_callable=mock_open)
    @patch('katalyst.coding_agent.tools.read.os.path.isfile')
    @patch('katalyst.coding_agent.tools.read.os.path.exists')
    def test_read_with_line_range(self, mock_exists, mock_isfile, mock_file):
        """Test reading specific line range"""
        mock_exists.return_value = True
        mock_isfile.return_value = True
        
        # Mock file with multiple lines
        file_content = ["Line 1\n", "Line 2\n", "Line 3\n", "Line 4\n", "Line 5\n"]
        # Create a side effect that returns a fresh iterator each time
        mock_file.return_value.__enter__.return_value.__iter__.side_effect = lambda: iter(file_content)
        
        result = read("test.txt", start_line=2, end_line=4)
        result_dict = json.loads(result)
        
        assert result_dict["content"] == "Line 2\nLine 3\nLine 4\n"
        assert result_dict["start_line"] == 2
        assert result_dict["end_line"] == 4

    def test_read_no_path(self):
        """Test error when no path provided"""
        result = read("")
        result_dict = json.loads(result)
        
        assert "error" in result_dict
        assert "No path provided" in result_dict["error"]

    @patch('katalyst.coding_agent.tools.read.os.path.exists')
    def test_read_file_not_found(self, mock_exists):
        """Test error when file doesn't exist"""
        mock_exists.return_value = False
        
        result = read("nonexistent.txt")
        result_dict = json.loads(result)
        
        assert "error" in result_dict
        assert "File not found" in result_dict["error"]

    @patch('katalyst.coding_agent.tools.read.os.path.exists')
    @patch('katalyst.coding_agent.tools.read.os.path.isfile')
    def test_read_not_a_file(self, mock_isfile, mock_exists):
        """Test error when path is not a file"""
        mock_exists.return_value = True
        mock_isfile.return_value = False
        
        result = read("/some/directory")
        result_dict = json.loads(result)
        
        assert "error" in result_dict
        assert "not a file" in result_dict["error"].lower()

    @patch('katalyst.coding_agent.tools.read.open', new_callable=mock_open)
    @patch('katalyst.coding_agent.tools.read.os.path.isfile')
    @patch('katalyst.coding_agent.tools.read.os.path.exists')
    def test_read_unicode_decode_error(self, mock_exists, mock_isfile, mock_file):
        """Test handling of unicode decode errors"""
        mock_exists.return_value = True
        mock_isfile.return_value = True
        mock_file.side_effect = UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid')
        
        result = read("binary.bin")
        result_dict = json.loads(result)
        
        assert "error" in result_dict
        assert "binary" in result_dict["error"].lower() or "encoding" in result_dict["error"].lower()

    @patch('katalyst.coding_agent.tools.read.open', new_callable=mock_open)
    @patch('katalyst.coding_agent.tools.read.os.path.isfile')
    @patch('katalyst.coding_agent.tools.read.os.path.exists')
    def test_read_empty_line_range(self, mock_exists, mock_isfile, mock_file):
        """Test reading lines outside file range"""
        mock_exists.return_value = True
        mock_isfile.return_value = True
        
        file_content = ["Line 1\n", "Line 2\n"]
        mock_file.return_value.__enter__.return_value.__iter__.side_effect = lambda: iter(file_content)
        
        result = read("test.txt", start_line=10, end_line=20)
        result_dict = json.loads(result)
        
        assert result_dict["content"] == ""
        assert "info" in result_dict
        assert "No lines in specified range" in result_dict["info"]

    @patch('katalyst.coding_agent.tools.read.open', side_effect=Exception("Generic read error"))
    @patch('katalyst.coding_agent.tools.read.os.path.isfile')
    @patch('katalyst.coding_agent.tools.read.os.path.exists')
    def test_read_generic_error(self, mock_exists, mock_isfile, mock_file):
        """Test handling of generic read errors"""
        mock_exists.return_value = True
        mock_isfile.return_value = True
        
        result = read("test.txt")
        result_dict = json.loads(result)
        
        assert "error" in result_dict
        assert "Error reading file" in result_dict["error"]

    @patch('katalyst.coding_agent.tools.read.load_gitignore_patterns')
    @patch('katalyst.coding_agent.tools.read.open', new_callable=mock_open, read_data='test content')
    @patch('katalyst.coding_agent.tools.read.os.path.isfile')
    @patch('katalyst.coding_agent.tools.read.os.path.exists')
    def test_read_respects_gitignore(self, mock_exists, mock_isfile, mock_file, mock_load_gitignore):
        """Test that read respects gitignore by default"""
        mock_exists.return_value = True
        mock_isfile.return_value = True
        
        # Mock gitignore spec that matches our file
        mock_spec = Mock()
        mock_spec.match_file.return_value = True
        mock_load_gitignore.return_value = mock_spec
        
        result = read(".env")
        result_dict = json.loads(result)
        
        assert "error" in result_dict
        assert ".gitignore" in result_dict["error"]
        assert "respect_gitignore=False" in result_dict["error"]

    @patch('katalyst.coding_agent.tools.read.load_gitignore_patterns')
    @patch('katalyst.coding_agent.tools.read.open', new_callable=mock_open, read_data='secret content')
    @patch('katalyst.coding_agent.tools.read.os.path.isfile')
    @patch('katalyst.coding_agent.tools.read.os.path.exists')
    def test_read_ignores_gitignore_when_requested(self, mock_exists, mock_isfile, mock_file, mock_load_gitignore):
        """Test that read can bypass gitignore when respect_gitignore=False"""
        mock_exists.return_value = True
        mock_isfile.return_value = True
        
        # Mock gitignore spec that matches our file
        mock_spec = Mock()
        mock_spec.match_file.return_value = True
        mock_load_gitignore.return_value = mock_spec
        
        result = read(".env", respect_gitignore=False)
        result_dict = json.loads(result)
        
        assert "content" in result_dict
        assert result_dict["content"] == "secret content"
        # Should not call gitignore check
        mock_load_gitignore.assert_not_called()

    @patch('katalyst.coding_agent.tools.read.load_gitignore_patterns')
    @patch('katalyst.coding_agent.tools.read.open', new_callable=mock_open, read_data='allowed content')
    @patch('katalyst.coding_agent.tools.read.os.path.isfile')
    @patch('katalyst.coding_agent.tools.read.os.path.exists')
    def test_read_non_gitignored_file(self, mock_exists, mock_isfile, mock_file, mock_load_gitignore):
        """Test that read works normally for non-gitignored files"""
        mock_exists.return_value = True
        mock_isfile.return_value = True
        
        # Mock gitignore spec that doesn't match our file
        mock_spec = Mock()
        mock_spec.match_file.return_value = False
        mock_load_gitignore.return_value = mock_spec
        
        result = read("allowed.txt")
        result_dict = json.loads(result)
        
        assert "content" in result_dict
        assert result_dict["content"] == "allowed content"