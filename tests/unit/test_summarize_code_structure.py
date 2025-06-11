import os
import pytest
import json
from pathlib import Path
from src.coding_agent.tools.summarize_code_structure import summarize_code_structure

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "test_data" / "summarize_code_structure"


@pytest.fixture(scope="module")
def setup_test_files():
    """Create test files for summarization."""
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
This is a test project for the summarize_code_structure tool.
""")

    yield

    # Cleanup
    for file in TEST_DATA_DIR.glob("*"):
        file.unlink()
    TEST_DATA_DIR.rmdir()


@pytest.mark.asyncio
async def test_summarize_single_file(setup_test_files):
    """Test summarizing a single file."""
    result = await summarize_code_structure(str(TEST_DATA_DIR / "test_module.py"))

    assert "summaries" in result
    assert len(result["summaries"]) == 1

    summary = result["summaries"][0]
    assert summary["file_path"] == str(TEST_DATA_DIR / "test_module.py")
    assert "TestClass" in summary["key_classes"]
    assert "main" in summary["key_functions"]
    assert "helper_function" in summary["key_functions"]
    assert len(summary["summary"]) > 0


@pytest.mark.asyncio
async def test_summarize_directory(setup_test_files):
    """Test summarizing an entire directory."""
    result = await summarize_code_structure(str(TEST_DATA_DIR))

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
async def test_nonexistent_path():
    """Test behavior with nonexistent path."""
    result = await summarize_code_structure("nonexistent/path")
    assert "error" in result
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_empty_directory(tmp_path):
    """Test behavior with empty directory."""
    result = await summarize_code_structure(str(tmp_path))
    assert "error" in result
    assert "no files to summarize" in result["error"].lower()


@pytest.mark.asyncio
async def test_respect_gitignore(setup_test_files):
    """Test that gitignore patterns are respected."""
    # Create a .gitignore file
    gitignore_path = TEST_DATA_DIR / ".gitignore"
    with open(gitignore_path, "w") as f:
        f.write("*.pyc\n__pycache__/\n")

    # Create a file that should be ignored
    ignored_path = TEST_DATA_DIR / "ignored.pyc"
    with open(ignored_path, "w") as f:
        f.write("This should be ignored")

    result = await summarize_code_structure(str(TEST_DATA_DIR), respect_gitignore=True)

    # Cleanup
    gitignore_path.unlink()
    ignored_path.unlink()

    # Verify ignored file is not in summaries
    summaries = result["summaries"]
    assert not any("ignored.pyc" in s["file_path"] for s in summaries)
