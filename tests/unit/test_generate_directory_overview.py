import os
import pytest
import json
from pathlib import Path
from src.coding_agent.tools.generate_directory_overview import (
    generate_directory_overview,
)

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "test_data" / "generate_directory_overview"


@pytest.fixture(scope="module")
def setup_test_files():
    """Create test files for directory overview generation."""
    # Create test directory if it doesn't exist
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Create a simple Python module
    module_path = TEST_DATA_DIR / "test_module.py"
    with open(module_path, "w") as f:
        f.write("""
class TestClass:
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        return self.value

def helper_function():
    return "helper"

def main():
    test = TestClass()
    return test.get_value()
""")

    # Create a simple README
    readme_path = TEST_DATA_DIR / "README.md"
    with open(readme_path, "w") as f:
        f.write("""
# Test Project
This is a test project for the generate_directory_overview tool.
""")

    yield

    # Cleanup
    for file in TEST_DATA_DIR.glob("*"):
        file.unlink()
    TEST_DATA_DIR.rmdir()


@pytest.mark.asyncio
async def test_generate_directory_overview_single_file(setup_test_files):
    """Test that generating an overview for a single file returns an error (only directories are allowed)."""
    result = await generate_directory_overview(str(TEST_DATA_DIR / "test_module.py"))
    assert "error" in result
    assert "directory" in result["error"].lower()


@pytest.mark.asyncio
async def test_generate_directory_overview_directory(setup_test_files):
    """Test generating an overview for an entire directory."""
    result = await generate_directory_overview(str(TEST_DATA_DIR))

    assert "summaries" in result
    assert len(result["summaries"]) >= 2  # Should include both Python and README files

    assert "overall_summary" in result
    assert len(result["overall_summary"]) > 0

    assert "main_components" in result
    assert len(result["main_components"]) > 0

    # Print the generated final summary for review
    # print("\n--- FINAL SUMMARY ---")
    # print("Overall Summary:", result["overall_summary"])
    # print("Main Components:", result["main_components"])

    # summaries = result["summaries"]


@pytest.mark.asyncio
async def test_generate_directory_overview_nonexistent_path():
    """Test behavior with nonexistent path."""
    result = await generate_directory_overview("nonexistent/path")
    assert "error" in result
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_generate_directory_overview_empty_directory(tmp_path):
    """Test behavior with empty directory."""
    result = await generate_directory_overview(str(tmp_path))
    assert "error" in result
    assert "no files to summarize" in result["error"].lower()


@pytest.mark.asyncio
async def test_generate_directory_overview_respect_gitignore(setup_test_files):
    """Test that gitignore patterns are respected."""
    # Create a .gitignore file
    gitignore_path = TEST_DATA_DIR / ".gitignore"
    with open(gitignore_path, "w") as f:
        f.write("*.pyc\n__pycache__/\n")

    # Create a file that should be ignored
    ignored_path = TEST_DATA_DIR / "ignored.pyc"
    with open(ignored_path, "w") as f:
        f.write("This should be ignored")

    result = await generate_directory_overview(
        str(TEST_DATA_DIR), respect_gitignore=True
    )

    # Cleanup
    gitignore_path.unlink()
    ignored_path.unlink()

    # Verify ignored file is not in summaries
    summaries = result["summaries"]
    assert not any("ignored.pyc" in s["file_path"] for s in summaries)
