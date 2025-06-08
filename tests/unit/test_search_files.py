import os
import shutil
import pytest
import json
from coding_agent.tools.search_files import regex_search_files


@pytest.fixture(autouse=True)
def sample_dir():
    # Setup
    os.makedirs("test_search_dir", exist_ok=True)
    with open("test_search_dir/file1.py", "w") as f:
        f.write("""
def foo():
    pass

class Bar:
    def baz(self):
        pass
""")
    with open("test_search_dir/file2.txt", "w") as f:
        f.write("""
This is a text file.
foo bar baz
""")
    with open("test_search_dir/ignoreme.log", "w") as f:
        f.write("Should not match this.")
    yield
    # Teardown
    shutil.rmtree("test_search_dir")


def test_python_function_search():
    print("Testing regex_search_files for 'def' in .py files...")
    result = regex_search_files(
        path="test_search_dir",
        regex=r"def ",
        file_pattern="*.py",
    )
    print(result)
    data = json.loads(result)
    assert "matches" in data
    assert any(
        "def foo()" in m["content"] or "def baz(self):" in m["content"]
        for m in data["matches"]
    )


def test_no_match():
    print("Testing regex_search_files for a pattern that does not exist...")
    result = regex_search_files(
        path="test_search_dir",
        regex=r"not_in_file",
        file_pattern="*.py",
    )
    print(result)
    data = json.loads(result)
    if "matches" in data:
        assert len(data["matches"]) == 0
    else:
        assert "info" in data and "No matches found" in data["info"]
