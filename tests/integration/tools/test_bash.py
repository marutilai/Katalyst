import pytest
import json
import sys
from katalyst.coding_agent.tools.bash import bash

pytestmark = pytest.mark.integration


def test_bash_success():
    """Test successful command execution"""
    # Use a cross-platform command
    cmd = "echo hello" if sys.platform != "win32" else "echo hello"
    result = bash(cmd, auto_approve=True)
    result_dict = json.loads(result)
    
    assert result_dict["success"] is True
    assert result_dict["stdout"] == "hello"
    assert result_dict["command"] == cmd


def test_bash_with_cwd():
    """Test command execution in specific directory"""
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test file
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")
        
        # List files in the temp directory
        result = bash("ls" if sys.platform != "win32" else "dir", cwd=tmpdir, auto_approve=True)
        result_dict = json.loads(result)
        
        assert result_dict["success"] is True
        assert "test.txt" in result_dict["stdout"]


def test_bash_command_not_found():
    """Test handling of non-existent command"""
    result = bash("nonexistent_command_xyz_123", auto_approve=True)
    result_dict = json.loads(result)
    
    assert result_dict["success"] is False
    assert "error" in result_dict
    # Command not found typically returns exit code 127
    assert "failed with code 127" in result_dict["error"] or "not found" in result_dict["error"].lower()


def test_bash_timeout():
    """Test command timeout"""
    # Use a command that takes time
    cmd = "sleep 5" if sys.platform != "win32" else "timeout /t 5"
    result = bash(cmd, timeout=1, auto_approve=True)
    result_dict = json.loads(result)
    
    assert result_dict["success"] is False
    assert "error" in result_dict
    assert "timed out" in result_dict["error"].lower()


def test_bash_stderr_capture():
    """Test capturing stderr output"""
    # Command that writes to stderr
    cmd = "ls /nonexistent_directory_xyz" if sys.platform != "win32" else "dir /nonexistent_directory_xyz"
    result = bash(cmd, auto_approve=True)
    result_dict = json.loads(result)
    
    assert result_dict["success"] is False
    if "stderr" in result_dict and result_dict["stderr"]:
        assert "cannot access" in result_dict["stderr"].lower() or "no such" in result_dict["stderr"].lower()


def test_bash_invalid_cwd():
    """Test handling of invalid working directory"""
    result = bash("echo test", cwd="/nonexistent/directory", auto_approve=True)
    result_dict = json.loads(result)
    
    assert result_dict["success"] is False
    assert "error" in result_dict
    assert "not a valid directory" in result_dict["error"]