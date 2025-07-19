import os
import json
import pytest
import stat
from katalyst.coding_agent.tools.ls import ls

pytestmark = pytest.mark.integration


def test_ls_basic(tmp_path):
    """Test basic ls functionality"""
    # Create test structure
    d = tmp_path / "testdir"
    d.mkdir()
    (d / "file1.txt").write_text("content1")
    (d / "file2.py").write_text("def main(): pass")
    subdir = d / "subdir"
    subdir.mkdir()
    
    result = ls(str(d))
    result_dict = json.loads(result)
    
    assert "entries" in result_dict
    entries = result_dict["entries"]
    assert len(entries) == 3
    
    # Check that files and directories are listed
    names = [e["name"] for e in entries]
    assert "file1.txt" in names
    assert "file2.py" in names
    assert "subdir/" in names  # Directory should have trailing slash


def test_ls_long_format(tmp_path):
    """Test long format output"""
    d = tmp_path / "testdir"
    d.mkdir()
    test_file = d / "test.txt"
    test_file.write_text("hello world")
    
    result = ls(str(d), long=True)
    result_dict = json.loads(result)
    
    assert "entries" in result_dict
    entry = result_dict["entries"][0]
    
    # Long format should include additional fields
    assert "size" in entry
    assert "permissions" in entry
    assert "modified" in entry
    assert entry["permissions"].startswith("-rw")  # Regular file


def test_ls_show_hidden(tmp_path):
    """Test showing hidden files"""
    d = tmp_path / "testdir"
    d.mkdir()
    (d / "visible.txt").write_text("visible")
    (d / ".hidden").write_text("hidden")
    (d / ".git").mkdir()
    
    # Without all flag
    result = ls(str(d), all=False)
    result_dict = json.loads(result)
    entries = result_dict["entries"]
    assert len(entries) == 1
    assert entries[0]["name"] == "visible.txt"
    
    # With all flag but respecting gitignore
    result = ls(str(d), all=True, respect_gitignore=True)
    result_dict = json.loads(result)
    entries = result_dict["entries"]
    # .git might be filtered by gitignore patterns
    assert len(entries) >= 2
    
    # With all flag and not respecting gitignore
    result = ls(str(d), all=True, respect_gitignore=False)
    result_dict = json.loads(result)
    entries = result_dict["entries"]
    names = [e["name"] for e in entries]
    assert ".hidden" in names
    assert ".git/" in names
    assert "visible.txt" in names


def test_ls_recursive(tmp_path):
    """Test recursive listing"""
    # Create nested structure
    d = tmp_path / "root"
    d.mkdir()
    (d / "file1.txt").write_text("top level")
    
    sub1 = d / "subdir1"
    sub1.mkdir()
    (sub1 / "file2.txt").write_text("in subdir1")
    
    sub2 = sub1 / "subdir2"
    sub2.mkdir()
    (sub2 / "file3.txt").write_text("deeply nested")
    
    result = ls(str(d), recursive=True)
    result_dict = json.loads(result)
    
    entries = result_dict["entries"]
    
    # Should have entries for all levels
    # Look for header entries that indicate directory sections
    headers = [e for e in entries if e.get("type") == "header"]
    assert len(headers) >= 1  # At least subdir1 header
    
    # Check that all files are listed
    all_names = []
    for entry in entries:
        if entry.get("type") != "header":
            all_names.append(entry["name"])
    
    # Should find files at different levels
    assert any("file1.txt" in name for name in all_names)
    assert any("file2.txt" in name for name in all_names)
    assert any("file3.txt" in name for name in all_names)


def test_ls_single_file(tmp_path):
    """Test listing a single file"""
    test_file = tmp_path / "single.txt"
    test_file.write_text("content")
    
    result = ls(str(test_file))
    result_dict = json.loads(result)
    
    assert "entries" in result_dict
    assert len(result_dict["entries"]) == 1
    assert result_dict["entries"][0]["name"] == "single.txt"
    assert result_dict["entries"][0]["type"] == "file"


def test_ls_nonexistent_path():
    """Test ls on non-existent path"""
    result = ls("/path/that/does/not/exist")
    result_dict = json.loads(result)
    
    assert "error" in result_dict
    assert "not found" in result_dict["error"].lower()


def test_ls_empty_directory(tmp_path):
    """Test listing empty directory"""
    d = tmp_path / "empty"
    d.mkdir()
    
    result = ls(str(d))
    result_dict = json.loads(result)
    
    assert "entries" in result_dict
    assert len(result_dict["entries"]) == 0


def test_ls_human_readable_sizes(tmp_path):
    """Test human readable size formatting"""
    d = tmp_path / "testdir"
    d.mkdir()
    
    # Create files of different sizes
    small_file = d / "small.txt"
    small_file.write_text("x" * 100)  # 100 bytes
    
    medium_file = d / "medium.txt"
    medium_file.write_text("x" * 2048)  # 2KB
    
    result = ls(str(d), long=True, human_readable=True)
    result_dict = json.loads(result)
    
    entries = {e["name"]: e for e in result_dict["entries"]}
    
    # Check human readable formatting
    assert "B" in entries["small.txt"]["size"] or "100" in entries["small.txt"]["size"]
    assert "K" in entries["medium.txt"]["size"] or "2" in entries["medium.txt"]["size"]


def test_ls_permissions(tmp_path):
    """Test permission display in long format"""
    d = tmp_path / "testdir"
    d.mkdir()
    
    # Create a file and make it executable
    script = d / "script.sh"
    script.write_text("#!/bin/bash\necho hello")
    script.chmod(0o755)
    
    result = ls(str(d), long=True)
    result_dict = json.loads(result)
    
    entry = result_dict["entries"][0]
    perms = entry["permissions"]
    
    # Should show as executable
    assert perms[0] == "-"  # Regular file
    assert "x" in perms  # Has execute permission