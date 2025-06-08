import os
import json
from coding_agent.tools.apply_source_code_diff import apply_source_code_diff


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


if __name__ == "__main__":
    test_apply_source_code_diff_success()
    test_apply_source_code_diff_syntax_error()
    test_apply_source_code_diff_search_mismatch()
    print("All apply_source_code_diff tests passed.")
