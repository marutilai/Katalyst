"""Unit tests for edit tool"""

import pytest
import json
import os
from unittest.mock import patch, mock_open
from katalyst.coding_agent.tools.edit import edit
os.environ['KATALYST_LOG_LEVEL'] = 'ERROR'


class TestEditTool:
    """Test cases for edit tool"""

    @patch('katalyst.coding_agent.tools.edit.check_syntax')
    @patch('katalyst.coding_agent.tools.edit.open', new_callable=mock_open, read_data='DEBUG = False\nPORT = 3000')
    @patch('katalyst.coding_agent.tools.edit.os.path.exists')
    def test_edit_success(self, mock_exists, mock_file, mock_check_syntax):
        """Test successful single edit"""
        mock_exists.return_value = True
        mock_check_syntax.return_value = None  # No syntax error
        
        result = edit("config.py", "DEBUG = False", "DEBUG = True")
        result_dict = json.loads(result)
        
        assert result_dict["success"] is True
        assert "Replaced 1 occurrence" in result_dict["info"]
        
        # Verify write was called with new content
        mock_file().write.assert_called_with('DEBUG = True\nPORT = 3000')

    def test_edit_no_file_path(self):
        """Test error when no file path provided"""
        result = edit("", "old", "new")
        result_dict = json.loads(result)
        
        assert result_dict["success"] is False
        assert "No file_path provided" in result_dict["error"]

    def test_edit_identical_strings(self):
        """Test error when old and new strings are identical"""
        result = edit("file.py", "same", "same")
        result_dict = json.loads(result)
        
        assert result_dict["success"] is False
        assert "identical" in result_dict["error"]

    @patch('katalyst.coding_agent.tools.edit.os.path.exists')
    def test_edit_file_not_found(self, mock_exists):
        """Test error when file doesn't exist"""
        mock_exists.return_value = False
        
        result = edit("missing.py", "old", "new")
        result_dict = json.loads(result)
        
        assert result_dict["success"] is False
        assert "File not found" in result_dict["error"]

    @patch('katalyst.coding_agent.tools.edit.open', new_callable=mock_open, read_data='Hello world')
    @patch('katalyst.coding_agent.tools.edit.os.path.exists')
    def test_edit_string_not_found(self, mock_exists, mock_file):
        """Test error when string not found"""
        mock_exists.return_value = True
        
        result = edit("file.txt", "missing", "new")
        result_dict = json.loads(result)
        
        assert result_dict["success"] is False
        assert "String not found" in result_dict["error"]

    @patch('katalyst.coding_agent.tools.edit.open', new_callable=mock_open, read_data='foo bar foo')
    @patch('katalyst.coding_agent.tools.edit.os.path.exists')
    def test_edit_multiple_occurrences(self, mock_exists, mock_file):
        """Test error when string appears multiple times"""
        mock_exists.return_value = True
        
        result = edit("file.txt", "foo", "baz")
        result_dict = json.loads(result)
        
        assert result_dict["success"] is False
        assert "found 2 times" in result_dict["error"]
        assert "MultiEdit" in result_dict["error"]

    @patch('katalyst.coding_agent.tools.edit.check_syntax')
    @patch('katalyst.coding_agent.tools.edit.open', new_callable=mock_open, read_data='def foo(')
    @patch('katalyst.coding_agent.tools.edit.os.path.exists')
    def test_edit_syntax_error(self, mock_exists, mock_file, mock_check_syntax):
        """Test syntax error detection"""
        mock_exists.return_value = True
        mock_check_syntax.return_value = "SyntaxError: invalid syntax"
        
        result = edit("test.py", "def foo(", "def foo():")
        result_dict = json.loads(result)
        
        assert result_dict["success"] is False
        assert "Syntax error" in result_dict["error"]