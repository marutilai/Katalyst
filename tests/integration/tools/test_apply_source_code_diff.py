import os
import json
import pytest
from katalyst.coding_agent.tools.apply_source_code_diff import apply_source_code_diff

pytestmark = pytest.mark.integration


def write_sample_file(filename, content):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)


def read_file(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()


def test_apply_source_code_diff_success():
    # Create a simple Python file
    fname = "test_apply_source_code_diff_sample.py"
    original_code = "def foo():\n    return 1\n"
    write_sample_file(fname, original_code)
    # Prepare a diff to change return value
    diff = """
<<<<<<< SEARCH
:start_line:1
-------
def foo():
    return 1
=======
def foo():
    return 42
>>>>>>> REPLACE
"""
    result = apply_source_code_diff(fname, diff, auto_approve=True)
    print("Result (success):", result)
    updated_code = read_file(fname)
    assert "return 42" in updated_code
    data = json.loads(result)
    assert data["success"] is True
    os.remove(fname)


def test_apply_source_code_diff_syntax_error():
    # Create a simple Python file
    fname = "test_apply_source_code_diff_syntax.py"
    original_code = "def bar():\n    return 2\n"
    write_sample_file(fname, original_code)
    # Prepare a diff that introduces a syntax error
    diff = """
<<<<<<< SEARCH
:start_line:1
-------
def bar():
    return 2
=======
def bar(
    return 2
)
>>>>>>> REPLACE
"""
    result = apply_source_code_diff(fname, diff, auto_approve=True)
    print("Result (syntax error):", result)
    data = json.loads(result)
    assert data["success"] is False
    assert "error" in data
    os.remove(fname)


def test_apply_source_code_diff_search_mismatch():
    # Create a simple Python file
    fname = "test_apply_source_code_diff_mismatch.py"
    original_code = "def baz():\n    return 3\n"
    write_sample_file(fname, original_code)
    # Prepare a diff with wrong search content
    diff = """
<<<<<<< SEARCH
:start_line:1
-------
def baz():
    return 999
=======
def baz():
    return 0
>>>>>>> REPLACE
"""
    result = apply_source_code_diff(fname, diff, auto_approve=True)
    print("Result (search mismatch):", result)
    data = json.loads(result)
    assert data["success"] is False
    assert "error" in data
    os.remove(fname)


def test_fuzzy_match_minor_differences():
    """Test fuzzy matching with minor differences like whitespace or typos."""
    fname = "test_fuzzy_match_minor.py"
    original_code = """def calculate_total(items):
    # Calculate the total price
    total = 0
    for item in items:
        total += item.price
    return total
"""
    write_sample_file(fname, original_code)
    
    # Diff with minor whitespace difference (missing comment, extra space)
    diff = """<<<<<<< SEARCH
:start_line:1
-------
def calculate_total(items):
    #Calculate the total price
    total = 0
    for item in items:
        total +=  item.price
    return total
=======
def calculate_total(items):
    # Calculate the total price with tax
    total = 0
    for item in items:
        total += item.price * 1.1  # 10% tax
    return total
>>>>>>> REPLACE
"""
    result = apply_source_code_diff(fname, diff, auto_approve=True)
    data = json.loads(result)
    assert data["success"] is True
    updated_code = read_file(fname)
    assert "total += item.price * 1.1" in updated_code
    assert "10% tax" in updated_code
    os.remove(fname)


def test_fuzzy_match_line_offset():
    """Test fuzzy matching when code has moved to a different line."""
    fname = "test_fuzzy_match_offset.py"
    original_code = """# File header comment

def helper_function():
    pass

def process_data(data):
    # Process the data
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result

def main():
    pass
"""
    write_sample_file(fname, original_code)
    
    # Diff targeting wrong line number (says line 5 but actually at line 6)
    diff = """<<<<<<< SEARCH
:start_line:5
-------
def process_data(data):
    # Process the data
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result
=======
def process_data(data):
    # Process the data with filtering
    result = []
    for item in data:
        if item > 0:
            result.append(item * 3)  # Triple instead of double
    return result
>>>>>>> REPLACE
"""
    result = apply_source_code_diff(fname, diff, auto_approve=True)
    data = json.loads(result)
    assert data["success"] is True
    updated_code = read_file(fname)
    assert "result.append(item * 3)" in updated_code
    assert "Triple instead of double" in updated_code
    os.remove(fname)


def test_fuzzy_match_below_threshold():
    """Test that fuzzy matching fails when similarity is below threshold."""
    fname = "test_fuzzy_match_fail.py"
    original_code = """def original_function(x, y):
    return x + y
"""
    write_sample_file(fname, original_code)
    
    # Diff with completely different content
    diff = """<<<<<<< SEARCH
:start_line:1
-------
def completely_different(a, b, c):
    result = a * b / c
    return result ** 2
=======
def new_function():
    pass
>>>>>>> REPLACE
"""
    result = apply_source_code_diff(fname, diff, auto_approve=True)
    data = json.loads(result)
    assert data["success"] is False
    assert "Fuzzy search" in data["error"]
    os.remove(fname)


def test_fuzzy_match_custom_threshold():
    """Test fuzzy matching with custom threshold."""
    fname = "test_fuzzy_custom_threshold.py"
    original_code = """def greet(name):
    print(f"Hello, {name}!")
"""
    write_sample_file(fname, original_code)
    
    # Diff with moderate differences
    diff = """<<<<<<< SEARCH
:start_line:1
-------
def greet(username):
    print(f"Hi, {username}!")
=======
def greet(name):
    print(f"Welcome, {name}!")
>>>>>>> REPLACE
"""
    # First try with high threshold (should fail)
    result = apply_source_code_diff(fname, diff, auto_approve=True, fuzzy_threshold=98)
    data = json.loads(result)
    assert data["success"] is False
    
    # Now try with lower threshold (should succeed)
    result = apply_source_code_diff(fname, diff, auto_approve=True, fuzzy_threshold=75)
    data = json.loads(result)
    assert data["success"] is True
    updated_code = read_file(fname)
    assert "Welcome," in updated_code
    os.remove(fname)


def test_multiple_fuzzy_matches():
    """Test multiple fuzzy matches in a single diff."""
    fname = "test_multiple_fuzzy.py"
    original_code = """class Calculator:
    def add(self, a, b):
        # Addition method
        return a + b
    
    def subtract(self, a, b):
        # Subtraction method
        return a - b
    
    def multiply(self, a, b):
        # Multiplication method
        return a * b
"""
    write_sample_file(fname, original_code)
    
    # Multiple diffs with minor variations
    diff = """<<<<<<< SEARCH
:start_line:2
-------
    def add(self, a, b):
        #Addition method
        return a + b
=======
    def add(self, a, b):
        # Addition method with logging
        print(f"Adding {a} + {b}")
        return a + b
>>>>>>> REPLACE
<<<<<<< SEARCH
:start_line:10
-------
    def multiply(self, a, b):
        #Multiplication method
        return a * b
=======
    def multiply(self, a, b):
        # Multiplication method with validation
        if b == 0:
            raise ValueError("Cannot multiply by zero")
        return a * b
>>>>>>> REPLACE
"""
    result = apply_source_code_diff(fname, diff, auto_approve=True)
    data = json.loads(result)
    assert data["success"] is True
    updated_code = read_file(fname)
    assert "Adding {a} + {b}" in updated_code
    assert "Cannot multiply by zero" in updated_code
    os.remove(fname)


if __name__ == "__main__":
    test_apply_source_code_diff_success()
    test_apply_source_code_diff_syntax_error()
    test_apply_source_code_diff_search_mismatch()
    test_fuzzy_match_minor_differences()
    test_fuzzy_match_line_offset()
    test_fuzzy_match_below_threshold()
    test_fuzzy_match_custom_threshold()
    test_multiple_fuzzy_matches()
    print("All apply_source_code_diff tests passed.")
