"""Unit tests for the ls tool"""

import pytest
import json
import os
from unittest.mock import patch, MagicMock
from katalyst.coding_agent.tools.ls import ls, _format_size, _format_permissions
import stat
from datetime import datetime


class TestLsTool:
    """Test cases for the ls tool"""

    @patch('katalyst.coding_agent.tools.ls.os.path.exists')
    @patch('katalyst.coding_agent.tools.ls.os.path.isfile')
    @patch('katalyst.coding_agent.tools.ls.os.path.isdir')
    @patch('katalyst.coding_agent.tools.ls.os.listdir')
    def test_ls_basic(self, mock_listdir, mock_isdir, mock_isfile, mock_exists):
        """Test basic ls functionality"""
        mock_exists.return_value = True
        mock_isfile.return_value = False
        mock_isdir.return_value = True
        mock_listdir.return_value = ['file1.txt', 'file2.py', 'subdir']
        
        # Mock isdir to return True only for 'subdir'
        mock_isdir.side_effect = lambda path: path.endswith('subdir') or path == '.'
        
        result = ls()
        result_dict = json.loads(result)
        
        assert "entries" in result_dict
        assert len(result_dict["entries"]) == 3
        # Check that directory has trailing slash
        names = [e["name"] for e in result_dict["entries"]]
        assert "subdir/" in names
        assert "file1.txt" in names

    @patch('katalyst.coding_agent.tools.ls.os.path.exists')
    @patch('katalyst.coding_agent.tools.ls.os.path.isfile')
    @patch('katalyst.coding_agent.tools.ls.os.path.isdir')
    @patch('katalyst.coding_agent.tools.ls.os.listdir')
    def test_ls_show_hidden(self, mock_listdir, mock_isdir, mock_isfile, mock_exists):
        """Test ls with all=True shows hidden files"""
        mock_exists.return_value = True
        mock_isfile.return_value = False
        mock_listdir.return_value = ['.hidden', 'visible.txt', '.git']
        
        # Configure isdir to return True for directories and the base path
        def is_directory(path):
            return path == '.' or path.endswith('.git')
        
        mock_isdir.side_effect = is_directory
        
        # Without all flag
        result = ls(all=False)
        result_dict = json.loads(result)
        assert len(result_dict["entries"]) == 1
        assert result_dict["entries"][0]["name"] == "visible.txt"
        
        # With all flag and respect_gitignore=False to see .git
        result = ls(all=True, respect_gitignore=False)
        result_dict = json.loads(result)
        assert len(result_dict["entries"]) == 3
        names = [e["name"] for e in result_dict["entries"]]
        assert ".hidden" in names
        assert ".git/" in names
        assert "visible.txt" in names

    @patch('katalyst.coding_agent.tools.ls.os.path.exists')
    @patch('katalyst.coding_agent.tools.ls.os.path.isfile')
    @patch('katalyst.coding_agent.tools.ls.os.stat')
    def test_ls_single_file(self, mock_stat, mock_isfile, mock_exists):
        """Test ls on a single file"""
        mock_exists.return_value = True
        mock_isfile.return_value = True
        
        # Mock file stats
        mock_stat.return_value = MagicMock(
            st_size=1024,
            st_mode=0o644 | stat.S_IFREG,
            st_mtime=1234567890
        )
        
        result = ls("test.txt")
        result_dict = json.loads(result)
        
        assert len(result_dict["entries"]) == 1
        assert result_dict["entries"][0]["name"] == "test.txt"
        assert result_dict["entries"][0]["type"] == "file"

    @patch('katalyst.coding_agent.tools.ls.os.path.exists')
    def test_ls_nonexistent_path(self, mock_exists):
        """Test ls with non-existent path"""
        mock_exists.return_value = False
        
        result = ls("/nonexistent")
        result_dict = json.loads(result)
        
        assert "error" in result_dict
        assert "Path not found" in result_dict["error"]

    def test_format_size_human_readable(self):
        """Test human readable size formatting"""
        assert _format_size(0, True) == "0.0B"
        assert _format_size(1023, True) == "1023.0B"
        assert _format_size(1024, True) == "1.0K"
        assert _format_size(1536, True) == "1.5K"
        assert _format_size(1048576, True) == "1.0M"
        assert _format_size(1073741824, True) == "1.0G"

    def test_format_size_not_human_readable(self):
        """Test non-human readable size formatting"""
        assert _format_size(1024, False) == "1024"
        assert _format_size(1048576, False) == "1048576"

    def test_format_permissions(self):
        """Test permission formatting"""
        # Regular file with 644 permissions
        mode = 0o644 | stat.S_IFREG
        assert _format_permissions(mode) == "-rw-r--r--"
        
        # Directory with 755 permissions
        mode = 0o755 | stat.S_IFDIR
        assert _format_permissions(mode) == "drwxr-xr-x"
        
        # Executable file
        mode = 0o755 | stat.S_IFREG
        assert _format_permissions(mode) == "-rwxr-xr-x"

    @patch('katalyst.coding_agent.tools.ls.os.walk')
    @patch('katalyst.coding_agent.tools.ls.os.path.exists')
    @patch('katalyst.coding_agent.tools.ls.os.path.isfile')
    def test_ls_recursive(self, mock_isfile, mock_exists, mock_walk):
        """Test recursive listing"""
        mock_exists.return_value = True
        mock_isfile.return_value = False
        
        # Mock os.walk output
        mock_walk.return_value = [
            ('.', ['subdir'], ['file1.txt']),
            ('./subdir', [], ['file2.txt'])
        ]
        
        result = ls(recursive=True)
        result_dict = json.loads(result)
        
        # Should have entries for both directories
        assert len(result_dict["entries"]) >= 3  # At least 1 header + 2 files
        
        # Check for header entry
        headers = [e for e in result_dict["entries"] if e.get("type") == "header"]
        assert len(headers) >= 1