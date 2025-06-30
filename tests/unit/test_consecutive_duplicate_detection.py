"""
Tests for consecutive duplicate tool call detection.
"""
import pytest
from katalyst.katalyst_core.utils.tool_repetition_detector import ToolRepetitionDetector


def test_consecutive_duplicate_detection():
    """Test that consecutive identical calls are immediately blocked."""
    detector = ToolRepetitionDetector()
    
    # First call should pass
    assert detector.check("read_file", {"path": "test.py"}) is True
    
    # Immediate duplicate should fail
    assert detector.check("read_file", {"path": "test.py"}) is False
    assert detector.is_consecutive_duplicate("read_file", {"path": "test.py"}) is True
    
    # Different tool should pass
    assert detector.check("write_file", {"path": "test.py", "content": "data"}) is True
    
    # Going back to read_file should pass (not consecutive)
    assert detector.check("read_file", {"path": "test.py"}) is True
    
    # But immediate duplicate again should fail
    assert detector.check("read_file", {"path": "test.py"}) is False


def test_consecutive_duplicate_with_different_inputs():
    """Test that same tool with different inputs is allowed."""
    detector = ToolRepetitionDetector()
    
    # First call
    assert detector.check("read_file", {"path": "file1.py"}) is True
    
    # Same tool, different input should pass
    assert detector.check("read_file", {"path": "file2.py"}) is True
    # After check(), file2 is now in history, so it will show as consecutive
    assert detector.is_consecutive_duplicate("read_file", {"path": "file2.py"}) is True
    
    # Now duplicate of file2 should fail
    assert detector.check("read_file", {"path": "file2.py"}) is False


def test_threshold_still_applies():
    """Test that the regular threshold still applies for non-consecutive duplicates."""
    # Use a threshold of 2 since default deque maxlen is 5
    detector = ToolRepetitionDetector(repetition_threshold=2)
    
    # Make 2 calls to tool_a interspersed with other tools
    assert detector.check("tool_a", {"param": "a"}) is True  # First A
    assert detector.check("tool_b", {"param": "b"}) is True  # Other tool
    assert detector.check("tool_a", {"param": "a"}) is True  # Second A (at threshold)
    assert detector.check("tool_c", {"param": "c"}) is True  # Other tool to break consecutive
    
    # Now the 3rd call to tool_a should fail (exceeds threshold of 2)
    # And it's not a consecutive duplicate since tool_c was last
    assert detector.is_consecutive_duplicate("tool_a", {"param": "a"}) is False
    assert detector.check("tool_a", {"param": "a"}) is False  # Third A exceeds threshold


def test_reset_clears_history():
    """Test that reset clears the detection history."""
    detector = ToolRepetitionDetector()
    
    # Make some calls
    assert detector.check("read_file", {"path": "test.py"}) is True
    assert detector.check("read_file", {"path": "test.py"}) is False  # This should fail
    
    # Reset
    detector.reset()
    
    # Now the same call should pass again
    assert detector.check("read_file", {"path": "test.py"}) is True
    # After the check, it's in history
    assert detector.is_consecutive_duplicate("read_file", {"path": "test.py"}) is True