import os
from src.coding_agent.tools.read_file import read_file


def write_sample_file(filename, content):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)


def test_read_file_success():
    fname = "test_read_file_sample.txt"
    content = "Hello\nWorld\nTest\n"
    write_sample_file(fname, content)
    result = read_file(fname, start_line=1, end_line=2)
    assert "Hello" in result and "World" in result
    os.remove(fname)


def test_read_file_missing():
    result = read_file("nonexistent.txt")
    assert "File not found" in result or "error" in result
