"""
Unit tests for ToolRepetitionDetector.
"""
import pytest
from katalyst.katalyst_core.utils.tool_repetition_detector import ToolRepetitionDetector


class TestToolRepetitionDetector:
    """Test cases for ToolRepetitionDetector."""
    
    def test_initialization(self):
        """Test detector initialization with default values."""
        detector = ToolRepetitionDetector()
        assert detector.repetition_threshold == 3
        assert len(detector.recent_calls) == 0
    
    def test_initialization_with_custom_threshold(self):
        """Test detector initialization with custom threshold."""
        detector = ToolRepetitionDetector(repetition_threshold=5)
        assert detector.repetition_threshold == 5
    
    def test_no_repetition(self):
        """Test that different tool calls are not flagged as repetitions."""
        detector = ToolRepetitionDetector()
        
        # Different tools
        assert detector.check("read_file", {"path": "file1.py"}) is True
        assert detector.check("write_to_file", {"path": "file2.py", "content": "test"}) is True
        assert detector.check("list_files", {"path": ".", "recursive": False}) is True
        
        # Same tool but different inputs
        assert detector.check("read_file", {"path": "file2.py"}) is True
        assert detector.check("read_file", {"path": "file3.py"}) is True
    
    def test_repetition_detection(self):
        """Test that identical tool calls are detected as repetitions."""
        detector = ToolRepetitionDetector(repetition_threshold=3)
        
        # First call - should pass
        assert detector.check("read_file", {"path": "test.py"}) is True
        
        # Second call - should pass
        assert detector.check("read_file", {"path": "test.py"}) is True
        
        # Third call - should pass (at threshold)
        assert detector.check("read_file", {"path": "test.py"}) is True
        
        # Fourth call - should fail (exceeds threshold)
        assert detector.check("read_file", {"path": "test.py"}) is False
        
        # Fifth call - should still fail
        assert detector.check("read_file", {"path": "test.py"}) is False
    
    def test_repetition_count(self):
        """Test getting the repetition count for a specific call."""
        detector = ToolRepetitionDetector()
        
        # No calls yet
        assert detector.get_repetition_count("read_file", {"path": "test.py"}) == 0
        
        # Make some calls
        detector.check("read_file", {"path": "test.py"})
        assert detector.get_repetition_count("read_file", {"path": "test.py"}) == 1
        
        detector.check("read_file", {"path": "test.py"})
        assert detector.get_repetition_count("read_file", {"path": "test.py"}) == 2
        
        # Different call shouldn't affect count
        detector.check("write_to_file", {"path": "other.py", "content": "data"})
        assert detector.get_repetition_count("read_file", {"path": "test.py"}) == 2
    
    def test_reset(self):
        """Test that reset clears the history."""
        detector = ToolRepetitionDetector()
        
        # Add some calls
        detector.check("read_file", {"path": "test.py"})
        detector.check("read_file", {"path": "test.py"})
        assert detector.get_repetition_count("read_file", {"path": "test.py"}) == 2
        
        # Reset
        detector.reset()
        assert len(detector.recent_calls) == 0
        assert detector.get_repetition_count("read_file", {"path": "test.py"}) == 0
        
        # Should be able to call again after reset
        assert detector.check("read_file", {"path": "test.py"}) is True
    
    def test_input_normalization(self):
        """Test that inputs with different key orders are treated as identical."""
        detector = ToolRepetitionDetector(repetition_threshold=2)
        
        # Same input with different key order
        input1 = {"path": "test.py", "recursive": True, "pattern": "*.py"}
        input2 = {"pattern": "*.py", "path": "test.py", "recursive": True}
        
        assert detector.check("list_files", input1) is True
        assert detector.check("list_files", input2) is True  # Should be counted as repetition
        assert detector.check("list_files", input1) is False  # Exceeds threshold
    
    def test_maxlen_behavior(self):
        """Test that old calls are removed when maxlen is reached."""
        detector = ToolRepetitionDetector()
        
        # Make 5 different calls (maxlen is 5)
        for i in range(5):
            detector.check("read_file", {"path": f"file{i}.py"})
        
        assert len(detector.recent_calls) == 5
        
        # Add one more - oldest should be removed
        detector.check("read_file", {"path": "file5.py"})
        assert len(detector.recent_calls) == 5
        
        # The first call should no longer be in history
        # So we can call it again without hitting repetition limit
        assert detector.check("read_file", {"path": "file0.py"}) is True
        assert detector.check("read_file", {"path": "file0.py"}) is True
    
    def test_complex_inputs(self):
        """Test handling of complex nested inputs."""
        detector = ToolRepetitionDetector()
        
        complex_input = {
            "path": "test.py",
            "options": {
                "encoding": "utf-8",
                "mode": "r"
            },
            "filters": ["*.py", "*.txt"]
        }
        
        # Should handle complex inputs without errors
        assert detector.check("complex_tool", complex_input) is True
        assert detector.get_repetition_count("complex_tool", complex_input) == 1
    
    def test_edge_case_empty_input(self):
        """Test handling of empty inputs."""
        detector = ToolRepetitionDetector()
        
        # Empty dict input
        assert detector.check("tool", {}) is True
        assert detector.check("tool", {}) is True
        assert detector.check("tool", {}) is True
        assert detector.check("tool", {}) is False  # Exceeds threshold
    
    def test_different_tools_same_input(self):
        """Test that same input to different tools is not considered repetition."""
        detector = ToolRepetitionDetector()
        
        input_dict = {"path": "test.py"}
        
        # Same input to different tools should not be repetition
        assert detector.check("read_file", input_dict) is True
        assert detector.check("delete_file", input_dict) is True
        assert detector.check("analyze_file", input_dict) is True
        
        # But same tool with same input should be
        assert detector.check("read_file", input_dict) is True
        assert detector.check("read_file", input_dict) is True
        assert detector.check("read_file", input_dict) is False  # Exceeds threshold