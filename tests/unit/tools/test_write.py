"""Unit tests for the write tool"""

import pytest
import json
import os
os.environ['KATALYST_LOG_LEVEL'] = 'ERROR'  # Disable debug logging for tests
from unittest.mock import patch, mock_open, MagicMock
from katalyst.coding_agent.tools.write import write


class TestWriteTool:
    """Test cases for the write tool"""

    @patch('katalyst.coding_agent.tools.write.check_execution_cancelled')
    @patch('katalyst.coding_agent.tools.write.os.path.exists')
    @patch('katalyst.coding_agent.tools.write.os.makedirs')
    @patch('katalyst.coding_agent.tools.write.open', new_callable=mock_open)
    def test_write_new_file(self, mock_file, mock_makedirs, mock_exists, mock_cancelled):
        """Test writing a new file"""
        mock_exists.return_value = False
        
        result = write("test.txt", "Hello, World!")
        result_dict = json.loads(result)
        
        assert result_dict["success"] is True
        assert result_dict["created"] is True
        assert result_dict["path"] == "test.txt"
        mock_file.assert_called_with("test.txt", 'w', encoding='utf-8')
        mock_file().write.assert_called_with("Hello, World!")

    @patch('katalyst.coding_agent.tools.write.check_execution_cancelled')
    @patch('katalyst.coding_agent.tools.write.os.path.exists')
    @patch('katalyst.coding_agent.tools.write.os.makedirs')
    @patch('katalyst.coding_agent.tools.write.open', new_callable=mock_open)
    def test_write_existing_file(self, mock_file, mock_makedirs, mock_exists, mock_cancelled):
        """Test overwriting an existing file"""
        mock_exists.return_value = True
        
        result = write("existing.txt", "New content")
        result_dict = json.loads(result)
        
        assert result_dict["success"] is True
        assert result_dict["created"] is False
        assert "Updated existing file" in result_dict["info"]

    def test_write_no_path(self):
        """Test error when no path provided"""
        result = write("", "content")
        result_dict = json.loads(result)
        
        assert result_dict["success"] is False
        assert "error" in result_dict
        assert "No path provided" in result_dict["error"]

    def test_write_no_content(self):
        """Test error when no content provided"""
        result = write("test.txt", None)
        result_dict = json.loads(result)
        
        assert result_dict["success"] is False
        assert "error" in result_dict
        assert "No content provided" in result_dict["error"]

    @patch('katalyst.coding_agent.tools.write.check_syntax')
    @patch('katalyst.coding_agent.tools.write.check_execution_cancelled')
    def test_write_syntax_error(self, mock_cancelled, mock_check_syntax):
        """Test handling syntax errors"""
        mock_check_syntax.return_value = "SyntaxError: invalid syntax"
        
        result = write("test.py", "def broken(")
        result_dict = json.loads(result)
        
        assert result_dict["success"] is False
        assert "error" in result_dict
        assert "Syntax error" in result_dict["error"]

    @patch('katalyst.coding_agent.tools.write.check_execution_cancelled')
    def test_write_cancelled(self, mock_cancelled):
        """Test handling cancelled operation"""
        mock_cancelled.side_effect = KeyboardInterrupt()
        
        result = write("test.txt", "content")
        result_dict = json.loads(result)
        
        assert result_dict["success"] is False
        assert result_dict["cancelled"] is True
        assert "cancelled by user" in result_dict["info"]

    @patch('katalyst.coding_agent.tools.write.check_execution_cancelled')
    @patch('katalyst.coding_agent.tools.write.os.path.exists')
    @patch('katalyst.coding_agent.tools.write.os.makedirs')
    @patch('katalyst.coding_agent.tools.write.open', side_effect=Exception("Write failed"))
    def test_write_error(self, mock_file, mock_makedirs, mock_exists, mock_cancelled):
        """Test handling write errors"""
        mock_exists.return_value = False
        
        result = write("test.txt", "content")
        result_dict = json.loads(result)
        
        assert result_dict["success"] is False
        assert "error" in result_dict
        assert "Write failed" in result_dict["error"]

    @patch('katalyst.coding_agent.tools.write.InputHandler')
    @patch('katalyst.coding_agent.tools.write.check_execution_cancelled')
    @patch('katalyst.coding_agent.tools.write.os.path.exists')
    def test_write_user_declined(self, mock_exists, mock_cancelled, mock_input_handler):
        """Test user declining to write"""
        mock_exists.return_value = False
        mock_input_handler.return_value.prompt_file_approval.return_value = False
        
        result = write("test.txt", "content", auto_approve=False)
        result_dict = json.loads(result)
        
        assert result_dict["success"] is False
        assert result_dict["cancelled"] is True
        assert "declined" in result_dict["info"]

    @patch('katalyst.coding_agent.tools.write.check_syntax')
    @patch('katalyst.coding_agent.tools.write.check_execution_cancelled')
    @patch('katalyst.coding_agent.tools.write.os.path.exists')
    @patch('katalyst.coding_agent.tools.write.os.makedirs')
    @patch('katalyst.coding_agent.tools.write.open', new_callable=mock_open)
    def test_write_create_parent_dirs(self, mock_file, mock_makedirs, mock_exists, mock_cancelled, mock_syntax):
        """Test creating parent directories"""
        mock_exists.return_value = False
        mock_syntax.return_value = None
        
        result = write("path/to/file.txt", "content")
        result_dict = json.loads(result)
        
        assert result_dict["success"] is True
        mock_makedirs.assert_called_with("path/to", exist_ok=True)