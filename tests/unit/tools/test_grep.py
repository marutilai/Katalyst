"""Unit tests for the grep tool"""

import pytest
import json
from unittest.mock import patch, MagicMock
from katalyst.coding_agent.tools.grep import grep


class TestGrepTool:
    """Test cases for the grep tool"""

    @patch('katalyst.coding_agent.tools.grep.subprocess.run')
    @patch('katalyst.coding_agent.tools.grep.which')
    @patch('katalyst.coding_agent.tools.grep.os.path.exists')
    def test_grep_basic_search(self, mock_exists, mock_which, mock_run):
        """Test basic grep functionality"""
        # Setup mocks
        mock_exists.return_value = True
        mock_which.return_value = '/usr/bin/rg'
        mock_run.return_value = MagicMock(
            stdout='file.py:10:def test_function():\nfile.py:20:def another_function():',
            stderr='',
            returncode=0
        )
        
        # Run grep
        result = grep("def", path="/test/path")
        result_dict = json.loads(result)
        
        # Assertions
        assert "matches" in result_dict
        assert len(result_dict["matches"]) == 2
        assert result_dict["matches"][0]["file"] == "file.py"
        assert result_dict["matches"][0]["line"] == 10
        assert result_dict["matches"][0]["content"] == "def test_function():"

    @patch('katalyst.coding_agent.tools.grep.subprocess.run')
    @patch('katalyst.coding_agent.tools.grep.which')
    @patch('katalyst.coding_agent.tools.grep.os.path.exists')
    def test_grep_case_insensitive(self, mock_exists, mock_which, mock_run):
        """Test case-insensitive search"""
        mock_exists.return_value = True
        mock_which.return_value = '/usr/bin/rg'
        mock_run.return_value = MagicMock(stdout='', stderr='', returncode=0)
        
        # Run grep with case_insensitive=True
        grep("PATTERN", case_insensitive=True)
        
        # Check that -i flag was included
        args = mock_run.call_args[0][0]
        assert "-i" in args

    @patch('katalyst.coding_agent.tools.grep.subprocess.run')
    @patch('katalyst.coding_agent.tools.grep.which')
    @patch('katalyst.coding_agent.tools.grep.os.path.exists')
    def test_grep_without_line_numbers(self, mock_exists, mock_which, mock_run):
        """Test search without line numbers"""
        mock_exists.return_value = True
        mock_which.return_value = '/usr/bin/rg'
        mock_run.return_value = MagicMock(
            stdout='file.py:content without line number',
            stderr='',
            returncode=0
        )
        
        # Run grep without line numbers
        result = grep("test", show_line_numbers=False)
        result_dict = json.loads(result)
        
        # Check result doesn't have line numbers
        assert "matches" in result_dict
        assert "line" not in result_dict["matches"][0]

    def test_grep_missing_pattern(self):
        """Test error when pattern is missing"""
        result = grep("")
        result_dict = json.loads(result)
        
        assert "error" in result_dict
        assert "Pattern is required" in result_dict["error"]

    @patch('katalyst.coding_agent.tools.grep.os.path.exists')
    def test_grep_invalid_path(self, mock_exists):
        """Test error when path doesn't exist"""
        mock_exists.return_value = False
        
        result = grep("test", path="/invalid/path")
        result_dict = json.loads(result)
        
        assert "error" in result_dict
        assert "Path not found" in result_dict["error"]

    @patch('katalyst.coding_agent.tools.grep.which')
    @patch('katalyst.coding_agent.tools.grep.os.path.exists')
    def test_grep_rg_not_installed(self, mock_exists, mock_which):
        """Test error when ripgrep is not installed"""
        mock_exists.return_value = True
        mock_which.return_value = None
        
        result = grep("test")
        result_dict = json.loads(result)
        
        assert "error" in result_dict
        assert "ripgrep" in result_dict["error"]

    @patch('katalyst.coding_agent.tools.grep.subprocess.run')
    @patch('katalyst.coding_agent.tools.grep.which')
    @patch('katalyst.coding_agent.tools.grep.os.path.exists')
    def test_grep_no_matches(self, mock_exists, mock_which, mock_run):
        """Test when no matches are found"""
        mock_exists.return_value = True
        mock_which.return_value = '/usr/bin/rg'
        mock_run.return_value = MagicMock(stdout='', stderr='', returncode=0)
        
        result = grep("nonexistent")
        result_dict = json.loads(result)
        
        assert "info" in result_dict
        assert "No matches found" in result_dict["info"]