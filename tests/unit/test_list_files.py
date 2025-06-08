import os
from coding_agent.tools.list_files import list_files


def test_list_files_success(tmp_path):
    d = tmp_path / "subdir"
    d.mkdir()
    (d / "file1.txt").write_text("abc")
    (d / "file2.py").write_text("def")
    result = list_files(str(d), recursive=False)
    assert "file1.txt" in result and "file2.py" in result


def test_list_files_nonexistent():
    result = list_files("no_such_dir", recursive=False)
    assert "Path does not exist" in result or "error" in result


def test_list_files_empty(tmp_path):
    d = tmp_path / "emptydir"
    d.mkdir()
    result = list_files(str(d), recursive=False)
    assert "files" in result and "[]" in result
