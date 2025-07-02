import os
import json
import pytest
from katalyst.coding_agent.tools.write_to_file import write_to_file

pytestmark = pytest.mark.integration


def test_write_to_file_basic():
    """Test basic write_to_file functionality."""
    fname = "test_basic_write.txt"
    content = "Line 1\nLine 2\nLine 3"
    result = write_to_file(fname, content, auto_approve=True)
    
    result_data = json.loads(result)
    assert result_data["success"] is True
    assert os.path.exists(fname)
    
    # Verify content was written correctly
    with open(fname, 'r') as f:
        written_content = f.read()
    assert written_content == content
    
    os.remove(fname)


def test_write_to_file_multiline_content():
    """Test write_to_file with multiline content."""
    fname = "test_multiline.txt"
    # Create content with 20 lines
    content = "\n".join([f"Line {i}" for i in range(1, 21)])
    
    result = write_to_file(fname, content, auto_approve=True)
    
    result_data = json.loads(result)
    assert result_data["success"] is True
    assert os.path.exists(fname)
    
    # Verify all lines were written
    with open(fname, 'r') as f:
        lines = f.readlines()
    assert len(lines) == 20
    
    os.remove(fname)


def test_write_to_file_empty_content():
    """Test write_to_file with empty content."""
    fname = "test_empty.txt"
    content = ""
    
    result = write_to_file(fname, content, auto_approve=True)
    
    result_data = json.loads(result)
    assert result_data["success"] is True
    assert os.path.exists(fname)
    
    # Verify empty file was created
    with open(fname, 'r') as f:
        written_content = f.read()
    assert written_content == ""
    
    os.remove(fname)


def test_write_to_file_large_content():
    """Test write_to_file with large content to ensure no truncation."""
    fname = "test_large.txt"
    # Create content with 1000 lines
    content = "\n".join([f"This is line {i} with some content to make it non-trivial" for i in range(1, 1001)])
    
    result = write_to_file(fname, content, auto_approve=True)
    
    result_data = json.loads(result)
    assert result_data["success"] is True
    assert os.path.exists(fname)
    
    # Verify all content was written
    with open(fname, 'r') as f:
        written_content = f.read()
    assert written_content == content
    assert len(written_content.split('\n')) == 1000
    
    os.remove(fname)