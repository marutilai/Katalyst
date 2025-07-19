"""Unit tests for multiedit tool"""

import pytest
import json
import os
from unittest.mock import patch, mock_open
from katalyst.coding_agent.tools.multiedit import multiedit
os.environ['KATALYST_LOG_LEVEL'] = 'ERROR'


class TestMultiEditTool:
    """Test cases for multiedit tool"""

    @patch('katalyst.coding_agent.tools.multiedit.check_syntax')
    @patch('katalyst.coding_agent.tools.multiedit.open', new_callable=mock_open, 
           read_data='DEBUG = False\nPORT = 3000\nHOST = localhost')
    @patch('katalyst.coding_agent.tools.multiedit.os.path.exists')
    def test_multiedit_success(self, mock_exists, mock_file, mock_check_syntax):
        """Test successful multiple edits"""
        mock_exists.return_value = True
        mock_check_syntax.return_value = None  # No syntax error
        
        edits = [
            {"old_string": "DEBUG = False", "new_string": "DEBUG = True"},
            {"old_string": "PORT = 3000", "new_string": "PORT = 8080"}
        ]
        
        result = multiedit("config.py", edits)
        result_dict = json.loads(result)
        
        assert result_dict["success"] is True
        assert "2 edits" in result_dict["info"]
        assert "2 total replacements" in result_dict["info"]

    def test_multiedit_no_file_path(self):
        """Test error when no file path provided"""
        result = multiedit("", [{"old_string": "a", "new_string": "b"}])
        result_dict = json.loads(result)
        
        assert result_dict["success"] is False
        assert "No file_path provided" in result_dict["error"]

    def test_multiedit_no_edits(self):
        """Test error when no edits provided"""
        result = multiedit("file.py", [])
        result_dict = json.loads(result)
        
        assert result_dict["success"] is False
        assert "No edits provided" in result_dict["error"]

    @patch('katalyst.coding_agent.tools.multiedit.os.path.exists')
    def test_multiedit_file_not_found(self, mock_exists):
        """Test error when file doesn't exist"""
        mock_exists.return_value = False
        
        result = multiedit("missing.py", [{"old_string": "a", "new_string": "b"}])
        result_dict = json.loads(result)
        
        assert result_dict["success"] is False
        assert "File not found" in result_dict["error"]

    @patch('katalyst.coding_agent.tools.multiedit.open', new_callable=mock_open, read_data='content')
    @patch('katalyst.coding_agent.tools.multiedit.os.path.exists')
    def test_multiedit_invalid_edit_format(self, mock_exists, mock_file):
        """Test error when edit format is invalid"""
        mock_exists.return_value = True
        
        # Test non-dict edit
        result = multiedit("file.txt", ["not a dict"])
        result_dict = json.loads(result)
        assert result_dict["success"] is False
        assert "not a dict" in result_dict["error"]
        
        # Test missing old_string
        result = multiedit("file.txt", [{"new_string": "b"}])
        result_dict = json.loads(result)
        assert result_dict["success"] is False
        assert "missing 'old_string'" in result_dict["error"]
        
        # Test missing new_string
        result = multiedit("file.txt", [{"old_string": "a"}])
        result_dict = json.loads(result)
        assert result_dict["success"] is False
        assert "missing 'new_string'" in result_dict["error"]

    @patch('katalyst.coding_agent.tools.multiedit.open', new_callable=mock_open, read_data='content')
    @patch('katalyst.coding_agent.tools.multiedit.os.path.exists')
    def test_multiedit_string_not_found(self, mock_exists, mock_file):
        """Test error when string not found"""
        mock_exists.return_value = True
        
        edits = [{"old_string": "missing", "new_string": "new"}]
        result = multiedit("file.txt", edits)
        result_dict = json.loads(result)
        
        assert result_dict["success"] is False
        assert "String not found" in result_dict["error"]

    @patch('katalyst.coding_agent.tools.multiedit.open', new_callable=mock_open, 
           read_data='foo bar foo baz foo')
    @patch('katalyst.coding_agent.tools.multiedit.os.path.exists')
    def test_multiedit_multiple_occurrences(self, mock_exists, mock_file):
        """Test replacing multiple occurrences"""
        mock_exists.return_value = True
        
        edits = [{"old_string": "foo", "new_string": "qux"}]
        result = multiedit("file.txt", edits)
        result_dict = json.loads(result)
        
        assert result_dict["success"] is True
        assert "3 total replacements" in result_dict["info"]
        
        # Verify all occurrences replaced
        mock_file().write.assert_called_with('qux bar qux baz qux')