"""Integration tests for the glob tool"""

import os
import json
import pytest
from katalyst.coding_agent.tools.glob import glob

pytestmark = pytest.mark.integration


def test_glob_simple_pattern(tmp_path):
    """Test simple glob pattern in a directory"""
    # Create test files
    (tmp_path / "test1.py").write_text("# Python file 1")
    (tmp_path / "test2.py").write_text("# Python file 2")
    (tmp_path / "data.json").write_text('{"key": "value"}')
    (tmp_path / "readme.md").write_text("# README")
    
    # Test finding Python files
    result = glob("*.py", path=str(tmp_path))
    result_dict = json.loads(result)
    
    assert len(result_dict["files"]) == 2
    assert "test1.py" in result_dict["files"]
    assert "test2.py" in result_dict["files"]
    assert "data.json" not in result_dict["files"]


def test_glob_recursive_pattern(tmp_path):
    """Test recursive glob patterns"""
    # Create nested directory structure
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("# Main")
    (tmp_path / "src" / "utils.py").write_text("# Utils")
    
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("# Test")
    
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "api.md").write_text("# API")
    
    # Test recursive Python file search
    result = glob("**/*.py", path=str(tmp_path))
    result_dict = json.loads(result)
    
    assert len(result_dict["files"]) == 3
    assert "src/main.py" in result_dict["files"]
    assert "src/utils.py" in result_dict["files"]
    assert "tests/test_main.py" in result_dict["files"]


def test_glob_character_patterns(tmp_path):
    """Test glob patterns with ? and []"""
    # Create files with specific patterns
    (tmp_path / "test1.txt").write_text("1")
    (tmp_path / "test2.txt").write_text("2")
    (tmp_path / "test3.txt").write_text("3")
    (tmp_path / "testA.txt").write_text("A")
    (tmp_path / "file.txt").write_text("file")
    
    # Test ? pattern
    result = glob("test?.txt", path=str(tmp_path))
    result_dict = json.loads(result)
    
    assert len(result_dict["files"]) == 4
    assert "test1.txt" in result_dict["files"]
    assert "testA.txt" in result_dict["files"]
    assert "file.txt" not in result_dict["files"]
    
    # Test [] pattern
    result = glob("test[1-3].txt", path=str(tmp_path))
    result_dict = json.loads(result)
    
    assert len(result_dict["files"]) == 3
    assert "test1.txt" in result_dict["files"]
    assert "test3.txt" in result_dict["files"]
    assert "testA.txt" not in result_dict["files"]


def test_glob_no_matches(tmp_path):
    """Test when no files match the pattern"""
    (tmp_path / "file.txt").write_text("content")
    
    result = glob("*.py", path=str(tmp_path))
    result_dict = json.loads(result)
    
    assert result_dict["files"] == []
    assert "info" in result_dict
    assert "No files found" in result_dict["info"]


def test_glob_respects_gitignore(tmp_path):
    """Test that glob respects gitignore patterns"""
    # Create gitignore
    (tmp_path / ".gitignore").write_text("*.log\nbuild/\nsecret.txt")
    
    # Create various files
    (tmp_path / "app.py").write_text("# App")
    (tmp_path / "debug.log").write_text("Debug info")
    (tmp_path / "secret.txt").write_text("Secret data")
    (tmp_path / "readme.txt").write_text("Public info")
    
    # Create build directory with files
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "output.js").write_text("Built file")
    
    # Test that gitignored files are excluded
    result = glob("*", path=str(tmp_path))
    result_dict = json.loads(result)
    
    assert "app.py" in result_dict["files"]
    assert "readme.txt" in result_dict["files"]
    assert "debug.log" not in result_dict["files"]
    assert "secret.txt" not in result_dict["files"]
    assert ".gitignore" in result_dict["files"]  # .gitignore itself is included
    
    # Test with respect_gitignore=False
    result = glob("*", path=str(tmp_path), respect_gitignore=False)
    result_dict = json.loads(result)
    
    assert "debug.log" in result_dict["files"]
    assert "secret.txt" in result_dict["files"]


def test_glob_directory_patterns(tmp_path):
    """Test patterns that match directories"""
    # Create directory structure
    (tmp_path / "src").mkdir()
    (tmp_path / "test").mkdir()
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "src" / "components").mkdir()
    
    # Directories should not be included by default
    result = glob("*", path=str(tmp_path))
    result_dict = json.loads(result)
    
    assert len(result_dict["files"]) == 0  # No files, only directories
    
    # Test explicit directory pattern
    result = glob("*/", path=str(tmp_path))
    result_dict = json.loads(result)
    
    # Note: Our implementation currently doesn't include directories
    # even with trailing slash, which is a limitation


def test_glob_complex_patterns(tmp_path):
    """Test more complex glob patterns"""
    # Create a realistic project structure
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "components").mkdir()
    (tmp_path / "src" / "components" / "Button.tsx").write_text("export Button")
    (tmp_path / "src" / "components" / "Input.tsx").write_text("export Input")
    (tmp_path / "src" / "components" / "button.test.tsx").write_text("test Button")
    
    (tmp_path / "src" / "utils").mkdir()
    (tmp_path / "src" / "utils" / "helpers.ts").write_text("helpers")
    (tmp_path / "src" / "utils" / "helpers.test.ts").write_text("test helpers")
    
    # Find all TypeScript files
    result = glob("**/*.ts", path=str(tmp_path))
    result_dict = json.loads(result)
    
    assert len(result_dict["files"]) == 2
    assert "src/utils/helpers.ts" in result_dict["files"]
    assert "src/utils/helpers.test.ts" in result_dict["files"]
    
    # Find all test files
    result = glob("**/*.test.*", path=str(tmp_path))
    result_dict = json.loads(result)
    
    assert len(result_dict["files"]) == 2
    assert "src/components/button.test.tsx" in result_dict["files"]
    assert "src/utils/helpers.test.ts" in result_dict["files"]
    
    # Find TSX files starting with uppercase
    result = glob("**/[A-Z]*.tsx", path=str(tmp_path))
    result_dict = json.loads(result)
    
    assert len(result_dict["files"]) == 2
    assert "src/components/Button.tsx" in result_dict["files"]
    assert "src/components/Input.tsx" in result_dict["files"]
    assert "src/components/button.test.tsx" not in result_dict["files"]


def test_glob_nonexistent_path():
    """Test error when base path doesn't exist"""
    result = glob("*.py", path="/nonexistent/path")
    result_dict = json.loads(result)
    
    assert "error" in result_dict
    assert "Base path not found" in result_dict["error"]


def test_glob_no_pattern():
    """Test error when no pattern provided"""
    result = glob("")
    result_dict = json.loads(result)
    
    assert "error" in result_dict
    assert "No pattern provided" in result_dict["error"]


def test_glob_current_directory():
    """Test glob with default current directory"""
    # This test runs in the actual file system
    # Just verify it doesn't error and returns valid JSON
    result = glob("*.md")
    result_dict = json.loads(result)
    
    assert "files" in result_dict
    assert "pattern" in result_dict
    assert "base_path" in result_dict
    assert isinstance(result_dict["files"], list)