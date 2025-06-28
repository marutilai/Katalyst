import pytest
from katalyst.katalyst_core.utils.fuzzy_match import find_fuzzy_match_in_lines, find_fuzzy_match_in_text

pytestmark = pytest.mark.unit


def test_find_fuzzy_match_in_text_exact():
    """Test exact match in text."""
    text = "Hello world, this is a test. Another line here."
    search = "this is a test"
    
    result = find_fuzzy_match_in_text(text, search, start_pos=0, window_size=100, threshold=95)
    assert result is not None
    start, end, score = result
    assert text[start:end] == search
    assert score == 100


def test_find_fuzzy_match_in_text_fuzzy():
    """Test fuzzy match in text with minor differences."""
    text = "The quick brown fox jumps over the lazy dog."
    search = "quick browm fox"  # Typo in 'brown'
    
    result = find_fuzzy_match_in_text(text, search, start_pos=0, window_size=100, threshold=85)
    assert result is not None
    start, end, score = result
    assert score > 85
    assert "quick brown fox" in text[start:end]


def test_find_fuzzy_match_in_text_window():
    """Test that window size limits search."""
    text = "A" * 100 + "target text here" + "B" * 100
    search = "target text here"
    
    # Search at beginning with small window (won't find target)
    result = find_fuzzy_match_in_text(text, search, start_pos=0, window_size=50, threshold=95)
    assert result is None
    
    # Search at beginning with large window (will find target)
    result = find_fuzzy_match_in_text(text, search, start_pos=0, window_size=150, threshold=95)
    assert result is not None
    start, end, score = result
    assert text[start:end] == search
    assert score == 100


def test_find_fuzzy_match_in_text_empty():
    """Test edge cases with empty inputs."""
    text = "Some text here"
    
    # Empty search
    result = find_fuzzy_match_in_text(text, "", start_pos=0, window_size=100, threshold=95)
    assert result is None
    
    # Empty text
    result = find_fuzzy_match_in_text("", "search", start_pos=0, window_size=100, threshold=95)
    assert result is None