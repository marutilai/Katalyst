import os
from coding_agent.tools.write_to_file import write_to_file


def test_write_to_file_success():
    fname = "test_write_file.txt"
    content = "Hello, world!"
    result = write_to_file(fname, content, auto_approve=True)
    assert "success" in result and "true" in result.lower()
    assert os.path.exists(fname)
    os.remove(fname)


def test_write_to_file_missing_path():
    result = write_to_file("", "content", auto_approve=True)
    assert "No valid" in result or "error" in result


def test_write_to_file_missing_content():
    result = write_to_file("file.txt", None, auto_approve=True)
    assert "No valid" in result or "error" in result
