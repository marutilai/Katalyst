import os
import json
import pytest
from katalyst.coding_agent.tools.write_to_file import write_to_file

pytestmark = pytest.mark.integration


def test_write_to_file_with_valid_line_count():
    """Test write_to_file with correct line count."""
    fname = "test_line_count.txt"
    content = "Line 1\nLine 2\nLine 3"
    result = write_to_file(fname, content, line_count=3, auto_approve=True)
    
    result_data = json.loads(result)
    assert result_data["success"] is True
    assert os.path.exists(fname)
    
    # Verify content was written correctly
    with open(fname, 'r') as f:
        written_content = f.read()
    assert written_content == content
    
    os.remove(fname)


def test_write_to_file_with_invalid_line_count():
    """Test write_to_file detects truncation with incorrect line count."""
    fname = "test_truncation.txt"
    content = "Line 1\nLine 2\nLine 3"
    
    # Claim we have 10 lines when we only have 3
    result = write_to_file(fname, content, line_count=10, auto_approve=True)
    
    result_data = json.loads(result)
    assert result_data["success"] is False
    assert "[CONTENT_OMISSION]" in result_data["error"]
    assert "LLM predicted 10 lines, but provided 3 lines" in result_data["error"]
    
    # File should not be created
    assert not os.path.exists(fname)


def test_write_to_file_within_tolerance():
    """Test write_to_file allows small differences within tolerance."""
    fname = "test_tolerance.txt"
    # Create content with 20 lines
    content = "\n".join([f"Line {i}" for i in range(1, 21)])
    
    # Tolerance is max(5, 5% of 20) = max(5, 1) = 5 lines
    # So 21 lines (off by 1) should pass
    result = write_to_file(fname, content, line_count=21, auto_approve=True)
    
    result_data = json.loads(result)
    assert result_data["success"] is True
    assert os.path.exists(fname)
    
    os.remove(fname)


def test_write_to_file_backward_compatibility():
    """Test write_to_file works without line_count for backward compatibility."""
    fname = "test_no_line_count.txt"
    content = "Backward compatible content"
    
    # Should work without line_count
    result = write_to_file(fname, content, auto_approve=True)
    
    result_data = json.loads(result)
    assert result_data["success"] is True
    assert os.path.exists(fname)
    
    os.remove(fname)