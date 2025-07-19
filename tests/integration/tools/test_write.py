import os
import json
import pytest
import shutil
from katalyst.coding_agent.tools.write import write

pytestmark = pytest.mark.integration


def test_write_new_file(tmp_path):
    """Test writing a new file"""
    test_file = tmp_path / "new_file.txt"
    content = "Hello, World!\nThis is a test."
    
    result = write(str(test_file), content)
    result_dict = json.loads(result)
    
    assert result_dict["success"] is True
    assert result_dict["created"] is True
    assert test_file.exists()
    assert test_file.read_text() == content


def test_write_overwrite_existing(tmp_path):
    """Test overwriting an existing file"""
    test_file = tmp_path / "existing.txt"
    test_file.write_text("Old content")
    
    new_content = "New content\nReplaced!"
    result = write(str(test_file), new_content)
    result_dict = json.loads(result)
    
    assert result_dict["success"] is True
    assert result_dict["created"] is False
    assert test_file.read_text() == new_content


def test_write_create_directories(tmp_path):
    """Test creating parent directories"""
    test_file = tmp_path / "deep" / "nested" / "dir" / "file.txt"
    content = "Content in nested directory"
    
    result = write(str(test_file), content)
    result_dict = json.loads(result)
    
    assert result_dict["success"] is True
    assert test_file.exists()
    assert test_file.parent.exists()
    assert test_file.read_text() == content


def test_write_python_syntax_check_valid(tmp_path):
    """Test writing valid Python code"""
    test_file = tmp_path / "valid.py"
    content = """def hello():
    print("Hello, World!")
    
if __name__ == "__main__":
    hello()
"""
    
    result = write(str(test_file), content)
    result_dict = json.loads(result)
    
    assert result_dict["success"] is True
    assert test_file.exists()


def test_write_python_syntax_check_invalid(tmp_path):
    """Test rejecting invalid Python syntax"""
    test_file = tmp_path / "invalid.py"
    content = """def hello()
    print("Missing colon above")
"""
    
    result = write(str(test_file), content)
    result_dict = json.loads(result)
    
    assert result_dict["success"] is False
    assert "error" in result_dict
    assert "syntax" in result_dict["error"].lower()
    assert not test_file.exists()


def test_write_no_path():
    """Test error when no path provided"""
    result = write("", "content")
    result_dict = json.loads(result)
    
    assert result_dict["success"] is False
    assert "error" in result_dict
    assert "path" in result_dict["error"].lower()


def test_write_no_content(tmp_path):
    """Test error when no content provided"""
    test_file = tmp_path / "no_content.txt"
    
    result = write(str(test_file), None)
    result_dict = json.loads(result)
    
    assert result_dict["success"] is False
    assert "error" in result_dict
    assert "content" in result_dict["error"].lower()


def test_write_empty_content(tmp_path):
    """Test writing empty content"""
    test_file = tmp_path / "empty.txt"
    
    result = write(str(test_file), "")
    result_dict = json.loads(result)
    
    assert result_dict["success"] is True
    assert test_file.exists()
    assert test_file.read_text() == ""


def test_write_unicode_content(tmp_path):
    """Test writing unicode content"""
    test_file = tmp_path / "unicode.txt"
    content = "Hello 世界! 🌍 Émojis and special chars: ñ, ü, ø"
    
    result = write(str(test_file), content)
    result_dict = json.loads(result)
    
    assert result_dict["success"] is True
    assert test_file.read_text(encoding='utf-8') == content


def test_write_large_file(tmp_path):
    """Test writing a large file"""
    test_file = tmp_path / "large.txt"
    # Create content with 1000 lines
    lines = [f"This is line number {i}" for i in range(1, 1001)]
    content = "\n".join(lines)
    
    result = write(str(test_file), content)
    result_dict = json.loads(result)
    
    assert result_dict["success"] is True
    assert test_file.exists()
    written_lines = test_file.read_text().split('\n')
    assert len(written_lines) == 1000


def test_write_json_file(tmp_path):
    """Test writing JSON content"""
    test_file = tmp_path / "data.json"
    content = '{\n  "name": "test",\n  "value": 42\n}'
    
    result = write(str(test_file), content)
    result_dict = json.loads(result)
    
    assert result_dict["success"] is True
    assert test_file.exists()
    # Verify it's valid JSON
    import json as json_module
    data = json_module.loads(test_file.read_text())
    assert data["name"] == "test"
    assert data["value"] == 42


def test_write_permission_error(tmp_path, monkeypatch):
    """Test handling permission errors"""
    test_file = tmp_path / "readonly.txt"
    
    # Mock open to raise permission error
    def mock_open(*args, **kwargs):
        raise PermissionError("Permission denied")
    
    monkeypatch.setattr("builtins.open", mock_open)
    
    result = write(str(test_file), "content")
    result_dict = json.loads(result)
    
    assert result_dict["success"] is False
    assert "error" in result_dict
    assert "Permission denied" in result_dict["error"]