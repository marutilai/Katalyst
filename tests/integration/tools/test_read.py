import os
import json
import pytest
from katalyst.coding_agent.tools.read import read

pytestmark = pytest.mark.integration


def test_read_entire_file(tmp_path):
    """Test reading an entire file"""
    test_file = tmp_path / "test.txt"
    content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
    test_file.write_text(content)
    
    result = read(str(test_file))
    result_dict = json.loads(result)
    
    assert "content" in result_dict
    assert result_dict["content"] == content
    assert "error" not in result_dict


def test_read_with_line_range(tmp_path):
    """Test reading specific line range"""
    test_file = tmp_path / "test.py"
    content = """def function1():
    pass

def function2():
    return True

def function3():
    print("hello")
"""
    test_file.write_text(content)
    
    # Read lines 4-5 (function2)
    result = read(str(test_file), start_line=4, end_line=5)
    result_dict = json.loads(result)
    
    assert "content" in result_dict
    assert "def function2():" in result_dict["content"]
    assert "return True" in result_dict["content"]
    assert "function1" not in result_dict["content"]
    assert "function3" not in result_dict["content"]
    assert result_dict.get("start_line") == 4
    assert result_dict.get("end_line") == 5


def test_read_from_start_line(tmp_path):
    """Test reading from a start line to end of file"""
    test_file = tmp_path / "numbered.txt"
    lines = [f"Line {i}\n" for i in range(1, 11)]
    test_file.write_text("".join(lines))
    
    result = read(str(test_file), start_line=7)
    result_dict = json.loads(result)
    
    assert "Line 7" in result_dict["content"]
    assert "Line 10" in result_dict["content"]
    assert "Line 6" not in result_dict["content"]
    assert result_dict.get("start_line") == 7


def test_read_to_end_line(tmp_path):
    """Test reading from beginning to an end line"""
    test_file = tmp_path / "numbered.txt"
    lines = [f"Line {i}\n" for i in range(1, 11)]
    test_file.write_text("".join(lines))
    
    result = read(str(test_file), end_line=3)
    result_dict = json.loads(result)
    
    assert "Line 1" in result_dict["content"]
    assert "Line 3" in result_dict["content"]
    assert "Line 4" not in result_dict["content"]
    assert result_dict.get("end_line") == 3


def test_read_nonexistent_file():
    """Test reading a file that doesn't exist"""
    result = read("/path/that/does/not/exist.txt")
    result_dict = json.loads(result)
    
    assert "error" in result_dict
    assert "not found" in result_dict["error"].lower()


def test_read_directory_instead_of_file(tmp_path):
    """Test error when trying to read a directory"""
    result = read(str(tmp_path))
    result_dict = json.loads(result)
    
    assert "error" in result_dict
    assert "not a file" in result_dict["error"].lower()


def test_read_empty_file(tmp_path):
    """Test reading an empty file"""
    test_file = tmp_path / "empty.txt"
    test_file.write_text("")
    
    result = read(str(test_file))
    result_dict = json.loads(result)
    
    assert "content" in result_dict
    assert result_dict["content"] == ""
    assert "error" not in result_dict


def test_read_out_of_range_lines(tmp_path):
    """Test reading lines outside file range"""
    test_file = tmp_path / "small.txt"
    test_file.write_text("Line 1\nLine 2\nLine 3")
    
    # Try to read lines 10-20 (beyond file)
    result = read(str(test_file), start_line=10, end_line=20)
    result_dict = json.loads(result)
    
    assert "content" in result_dict
    assert result_dict["content"] == ""
    assert "info" in result_dict
    assert "No lines in specified range" in result_dict["info"]


def test_read_no_path():
    """Test error when no path provided"""
    result = read("")
    result_dict = json.loads(result)
    
    assert "error" in result_dict
    assert "No path provided" in result_dict["error"]


def test_read_binary_file(tmp_path):
    """Test reading a binary file"""
    binary_file = tmp_path / "binary.bin"
    # Write some binary data
    binary_file.write_bytes(b'\x00\x01\x02\x03\xFF\xFE')
    
    result = read(str(binary_file))
    result_dict = json.loads(result)
    
    assert "error" in result_dict
    assert "binary" in result_dict["error"].lower() or "encoding" in result_dict["error"].lower()


def test_read_large_file_with_range(tmp_path):
    """Test reading a specific range from a large file"""
    test_file = tmp_path / "large.txt"
    
    # Create a file with 1000 lines
    lines = [f"This is line number {i}\n" for i in range(1, 1001)]
    test_file.write_text("".join(lines))
    
    # Read lines 500-510
    result = read(str(test_file), start_line=500, end_line=510)
    result_dict = json.loads(result)
    
    assert "content" in result_dict
    assert "line number 500" in result_dict["content"]
    assert "line number 510" in result_dict["content"]
    assert "line number 499" not in result_dict["content"]
    assert "line number 511" not in result_dict["content"]
    
    # Verify we only got 11 lines
    content_lines = result_dict["content"].strip().split('\n')
    assert len(content_lines) == 11


def test_read_respects_gitignore(tmp_path):
    """Test that read respects gitignore patterns"""
    # Create a .gitignore file
    gitignore_file = tmp_path / ".gitignore"
    gitignore_file.write_text("secrets.txt\n*.env\nconfig/private/*\n")
    
    # Create files that should be ignored
    secret_file = tmp_path / "secrets.txt"
    secret_file.write_text("secret data")
    
    env_file = tmp_path / "production.env"
    env_file.write_text("API_KEY=secret")
    
    # Create a file that should be readable
    normal_file = tmp_path / "readme.txt"
    normal_file.write_text("public content")
    
    # Test reading gitignored file (should fail)
    result = read(str(secret_file))
    result_dict = json.loads(result)
    assert "error" in result_dict
    assert ".gitignore" in result_dict["error"]
    
    # Test reading gitignored pattern file (should fail)
    result = read(str(env_file))
    result_dict = json.loads(result)
    assert "error" in result_dict
    assert ".gitignore" in result_dict["error"]
    
    # Test reading non-gitignored file (should succeed)
    result = read(str(normal_file))
    result_dict = json.loads(result)
    assert result_dict["content"] == "public content"
    
    # Test reading gitignored file with respect_gitignore=False (should succeed)
    result = read(str(secret_file), respect_gitignore=False)
    result_dict = json.loads(result)
    assert result_dict["content"] == "secret data"


def test_read_no_gitignore_file(tmp_path):
    """Test that read works normally when there's no .gitignore"""
    test_file = tmp_path / ".env"
    test_file.write_text("DATA=value")
    
    # Should read successfully when no .gitignore exists
    result = read(str(test_file))
    result_dict = json.loads(result)
    assert result_dict["content"] == "DATA=value"