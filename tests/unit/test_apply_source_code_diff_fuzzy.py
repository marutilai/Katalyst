import pytest
from katalyst.katalyst_core.utils.fuzzy_match import find_fuzzy_match_in_lines

pytestmark = pytest.mark.unit


def test_find_fuzzy_match_in_lines_exact():
    """Test that exact matches return 100% similarity."""
    lines = [
        "def foo():\n",
        "    return 1\n",
        "def bar():\n",
        "    return 2\n",
    ]
    search_lines = ["def foo():", "    return 1"]
    
    result = find_fuzzy_match_in_lines(lines, search_lines, start_line=1, buffer_size=20, threshold=95)
    assert result is not None
    index, score = result
    assert index == 0
    assert score == 100


def test_find_fuzzy_match_in_lines_with_whitespace():
    """Test fuzzy matching with whitespace differences."""
    lines = [
        "def calculate(x, y):\n",
        "    # Do calculation\n",
        "    result = x + y\n",
        "    return result\n",
    ]
    search_lines = [
        "def calculate(x,y):",  # Missing space
        "    #Do calculation",   # Missing space
        "    result=x+y",        # Missing spaces
        "    return result"
    ]
    
    result = find_fuzzy_match_in_lines(lines, search_lines, start_line=1, buffer_size=20, threshold=85)
    assert result is not None
    index, score = result
    assert index == 0
    assert score > 85


def test_find_fuzzy_match_in_lines_line_offset():
    """Test finding match when line number is off."""
    lines = [
        "# Header comment\n",
        "\n",
        "def target_function():\n",
        "    pass\n",
        "\n",
        "def other_function():\n",
        "    pass\n",
    ]
    search_lines = ["def target_function():", "    pass"]
    
    # Search at wrong line (1) but within buffer
    result = find_fuzzy_match_in_lines(lines, search_lines, start_line=1, buffer_size=5, threshold=95)
    assert result is not None
    index, score = result
    assert index == 2  # Actual location
    assert score == 100


def test_find_fuzzy_match_in_lines_no_match():
    """Test that no match is returned when similarity is below threshold."""
    lines = [
        "def foo():\n",
        "    return 1\n",
    ]
    search_lines = ["class Bar:", "    def __init__(self):"]
    
    result = find_fuzzy_match_in_lines(lines, search_lines, start_line=1, buffer_size=20, threshold=95)
    assert result is None


def test_find_fuzzy_match_in_lines_buffer_limits():
    """Test that search respects buffer limits."""
    lines = [f"line {i}\n" for i in range(100)]
    search_lines = ["line 50"]
    
    # Search at line 10 with small buffer (won't reach line 50)
    result = find_fuzzy_match_in_lines(lines, search_lines, start_line=10, buffer_size=10, threshold=95)
    assert result is None
    
    # Search at line 10 with large buffer (will reach line 50)
    result = find_fuzzy_match_in_lines(lines, search_lines, start_line=10, buffer_size=50, threshold=95)
    assert result is not None
    index, score = result
    assert index == 50
    assert score == 100


def test_find_fuzzy_match_in_lines_edge_cases():
    """Test edge cases like empty lines and boundaries."""
    lines = ["def foo():\n", "    pass\n"]
    
    # Search at end of file
    search_lines = ["def foo():", "    pass"]
    result = find_fuzzy_match_in_lines(lines, search_lines, start_line=1, buffer_size=5, threshold=95)
    assert result is not None
    
    # Search beyond file length
    result = find_fuzzy_match_in_lines(lines, search_lines, start_line=10, buffer_size=5, threshold=95)
    assert result is None
    
    # Empty search
    result = find_fuzzy_match_in_lines(lines, [], start_line=1, buffer_size=5, threshold=95)
    assert result is None


def test_find_fuzzy_match_in_lines_multiline_complex():
    """Test fuzzy matching with complex multiline code."""
    lines = [
        "class MyClass:\n",
        "    def __init__(self, name):\n", 
        "        self.name = name\n",
        "        self.items = []\n",
        "    \n",
        "    def add_item(self, item):\n",
        "        # Add item to list\n",
        "        self.items.append(item)\n",
        "        print(f'Added {item}')\n",
    ]
    
    # Search with minor differences
    search_lines = [
        "    def add_item(self,item):",  # Missing space
        "        #Add item to list",      # Missing space  
        "        self.items.append(item)",
        "        print(f'Added {item}')",
    ]
    
    result = find_fuzzy_match_in_lines(lines, search_lines, start_line=6, buffer_size=10, threshold=90)
    assert result is not None
    index, score = result
    assert index == 5  # 0-based index
    assert score > 90