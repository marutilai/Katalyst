import os
import shutil
import pytest
import json
from katalyst.coding_agent.tools.grep import grep

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def sample_dir():
    """Create test directory with sample files"""
    # Setup
    os.makedirs("test_grep_dir", exist_ok=True)
    
    # Python file with functions
    with open("test_grep_dir/code.py", "w") as f:
        f.write("""def hello():
    print("Hello World")
    
class MyClass:
    def method(self):
        return "test"

def another_function():
    # TODO: implement this
    pass
""")
    
    # Text file
    with open("test_grep_dir/notes.txt", "w") as f:
        f.write("""This is a text file.
It contains some TODO items.
And some regular text.
TODO: finish documentation
""")
    
    # Hidden file
    with open("test_grep_dir/.hidden", "w") as f:
        f.write("Hidden content with TODO")
    
    # File in subdirectory
    os.makedirs("test_grep_dir/subdir", exist_ok=True)
    with open("test_grep_dir/subdir/more.py", "w") as f:
        f.write("def subfunc():\n    pass")
    
    yield
    # Teardown
    shutil.rmtree("test_grep_dir")


def test_grep_basic_search():
    """Test basic pattern search"""
    result = grep("TODO", path="test_grep_dir")
    result_dict = json.loads(result)
    
    assert "matches" in result_dict
    matches = result_dict["matches"]
    assert len(matches) >= 2  # Should find TODO in code.py and notes.txt
    
    # Check that line numbers are included by default
    assert all("line" in match for match in matches)
    
    # Check content
    contents = [match["content"] for match in matches]
    assert any("TODO: implement this" in c for c in contents)
    assert any("TODO: finish documentation" in c for c in contents)


def test_grep_case_insensitive():
    """Test case-insensitive search"""
    # First, case-sensitive (default)
    result = grep("todo", path="test_grep_dir")
    result_dict = json.loads(result)
    
    if "matches" in result_dict:
        assert len(result_dict["matches"]) == 0
    
    # Now case-insensitive
    result = grep("todo", path="test_grep_dir", case_insensitive=True)
    result_dict = json.loads(result)
    
    assert "matches" in result_dict
    assert len(result_dict["matches"]) >= 2


def test_grep_file_pattern():
    """Test filtering by file pattern"""
    result = grep("def", path="test_grep_dir", file_pattern="*.py")
    result_dict = json.loads(result)
    
    assert "matches" in result_dict
    matches = result_dict["matches"]
    
    # Should only match Python files
    assert all(match["file"].endswith(".py") for match in matches)
    assert any("def hello():" in match["content"] for match in matches)


def test_grep_without_line_numbers():
    """Test search without line numbers"""
    result = grep("def", path="test_grep_dir", show_line_numbers=False)
    result_dict = json.loads(result)
    
    assert "matches" in result_dict
    matches = result_dict["matches"]
    
    # Should not have line numbers
    assert all("line" not in match for match in matches)
    assert all("content" in match for match in matches)


def test_grep_max_results():
    """Test limiting results"""
    result = grep("def", path="test_grep_dir", max_results=2)
    result_dict = json.loads(result)
    
    assert "matches" in result_dict
    assert len(result_dict["matches"]) <= 2
    
    if len(result_dict["matches"]) == 2:
        assert "info" in result_dict
        assert "truncated" in result_dict["info"].lower()


def test_grep_regex_pattern():
    """Test regex patterns"""
    # Search for class definitions
    result = grep(r"class\s+\w+:", path="test_grep_dir")
    result_dict = json.loads(result)
    
    assert "matches" in result_dict
    matches = result_dict["matches"]
    assert len(matches) >= 1
    assert any("class MyClass:" in match["content"] for match in matches)


def test_grep_no_matches():
    """Test when no matches are found"""
    result = grep("nonexistent_pattern_xyz", path="test_grep_dir")
    result_dict = json.loads(result)
    
    assert "info" in result_dict
    assert "No matches found" in result_dict["info"]


def test_grep_invalid_path():
    """Test with invalid path"""
    result = grep("test", path="/nonexistent/path")
    result_dict = json.loads(result)
    
    assert "error" in result_dict
    assert "not found" in result_dict["error"].lower()


def test_grep_empty_pattern():
    """Test with empty pattern"""
    result = grep("")
    result_dict = json.loads(result)
    
    assert "error" in result_dict
    assert "required" in result_dict["error"].lower()