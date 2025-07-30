"""Unit tests for file sandbox functionality."""

import os
import pytest
from unittest.mock import patch

from katalyst.katalyst_core.utils.file_utils import (
    resolve_and_validate_path,
    extract_file_paths,
    extract_and_classify_paths
)
from katalyst.katalyst_core.utils.exceptions import SandboxViolationError


class TestFilePathExtraction:
    """Test extracting file paths from user input."""
    
    def test_extract_absolute_paths(self):
        """Test extracting absolute Unix paths."""
        text = "Process /etc/hosts and /var/log/syslog"
        paths = extract_file_paths(text)
        assert paths == ["/etc/hosts", "/var/log/syslog"]
    
    def test_extract_home_paths(self):
        """Test extracting home directory paths."""
        text = "Check ~/Documents/report.pdf"
        paths = extract_file_paths(text)
        assert paths == ["~/Documents/report.pdf"]
    
    def test_extract_relative_paths(self):
        """Test extracting relative paths with parent references."""
        text = "Look at ../sibling/file.txt"
        paths = extract_file_paths(text)
        assert paths == ["../sibling/file.txt"]
    
    def test_no_duplicate_paths(self):
        """Test that duplicate paths are removed."""
        text = "Process /tmp/file.txt and again /tmp/file.txt"
        paths = extract_file_paths(text)
        assert paths == ["/tmp/file.txt"]
    
    def test_no_paths_in_text(self):
        """Test text without file paths."""
        text = "Just some regular text without paths"
        paths = extract_file_paths(text)
        assert paths == []


class TestSandboxValidation:
    """Test path sandbox validation."""
    
    @pytest.fixture
    def project_root(self, tmp_path):
        """Create a temporary project directory."""
        return str(tmp_path)
    
    def test_internal_path_allowed(self, project_root):
        """Test that internal paths are allowed."""
        internal_file = os.path.join(project_root, "src", "main.py")
        os.makedirs(os.path.dirname(internal_file), exist_ok=True)
        
        result = resolve_and_validate_path("src/main.py", project_root)
        assert result == internal_file
    
    def test_external_path_blocked(self, project_root):
        """Test that external paths are blocked by default."""
        with pytest.raises(SandboxViolationError) as exc_info:
            resolve_and_validate_path("/etc/passwd", project_root)
        
        assert "/etc/passwd" in str(exc_info.value)
        assert "outside the project directory" in str(exc_info.value)
    
    def test_external_path_allowed_with_permission(self, project_root):
        """Test that external paths work when explicitly allowed."""
        external_path = "/etc/hosts"
        allowed_paths = {external_path}
        
        # Should not raise an exception
        result = resolve_and_validate_path(external_path, project_root, allowed_paths)
        assert "/etc/hosts" in result  # May resolve to /private/etc/hosts on macOS
    
    def test_home_path_expansion(self, project_root):
        """Test that ~ is expanded correctly."""
        home_file = "~/test_file.txt"
        allowed_paths = [home_file]
        
        result = resolve_and_validate_path(home_file, project_root, allowed_paths)
        assert result.startswith(os.path.expanduser("~"))
        assert "test_file.txt" in result
    
    def test_parent_directory_traversal_blocked(self, project_root):
        """Test that parent directory traversal is blocked."""
        # Create a path that tries to escape the project
        escape_path = "../../../etc/passwd"
        
        with pytest.raises(SandboxViolationError):
            resolve_and_validate_path(escape_path, project_root)
    
    def test_allowed_paths_as_list_or_set(self, project_root):
        """Test that allowed_paths works with both list and set."""
        external_path = "/tmp/test.txt"
        
        # Test with list
        result_list = resolve_and_validate_path(
            external_path, project_root, [external_path]
        )
        
        # Test with set
        result_set = resolve_and_validate_path(
            external_path, project_root, {external_path}
        )
        
        assert result_list == result_set


class TestExtractAndClassifyPaths:
    """Test the combined extract and classify function."""
    
    @pytest.fixture
    def project_root(self, tmp_path):
        """Create a temporary project directory."""
        return str(tmp_path)
    
    def test_classify_external_paths(self, project_root):
        """Test classifying paths as internal or external."""
        text = f"Process {project_root}/internal.txt and /etc/hosts"
        external_paths = extract_and_classify_paths(text, project_root)
        
        # Only external path should be returned
        assert external_paths == ["/etc/hosts"]
    
    def test_classify_with_home_directory(self, project_root):
        """Test classifying home directory paths."""
        text = "Analyze ~/Downloads/data.csv"
        external_paths = extract_and_classify_paths(text, project_root)
        
        # Home directory should be classified as external
        assert len(external_paths) == 1
        # Path may be expanded or not, both are acceptable
        assert "Downloads/data.csv" in external_paths[0]
    
    def test_empty_list_when_no_external(self, project_root):
        """Test that empty list is returned when no external paths."""
        text = f"Just work with files in {project_root}/src"
        external_paths = extract_and_classify_paths(text, project_root)
        
        assert external_paths == []