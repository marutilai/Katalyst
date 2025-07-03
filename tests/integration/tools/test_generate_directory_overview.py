import os
import pytest
from katalyst.coding_agent.tools.generate_directory_overview import (
    generate_directory_overview,
)

pytestmark = pytest.mark.integration


@pytest.mark.integration
@pytest.mark.asyncio
async def test_generate_directory_overview_small_project(tmp_path):
    """
    Integration test: Run the tool on a small test project structure
    to verify it works end-to-end with the LangChain models.
    """
    # Create a small test project structure
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    
    # Create main.py
    (src_dir / "main.py").write_text("""
def main():
    '''Main entry point for the application'''
    print("Hello, World!")
    
if __name__ == "__main__":
    main()
""")
    
    # Create utils.py
    (src_dir / "utils.py").write_text("""
class Logger:
    '''Simple logger class'''
    def log(self, message):
        print(f"[LOG] {message}")

def format_date(date):
    '''Format a date object'''
    return date.strftime("%Y-%m-%d")
""")
    
    # Create test directory
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    (test_dir / "test_main.py").write_text("""
import pytest
from src.main import main

def test_main():
    '''Test the main function'''
    # Test passes if no exception
    main()
""")
    
    # Create README
    (tmp_path / "README.md").write_text("""
# Test Project

This is a test project for directory overview generation.

## Features
- Simple main function
- Basic utilities
- Unit tests
""")
    
    # Create .gitignore
    (tmp_path / ".gitignore").write_text("*.pyc\n__pycache__/\n.coverage")
    
    # Create a file that should be ignored
    (src_dir / "__pycache__").mkdir()
    (src_dir / "__pycache__" / "main.cpython-312.pyc").write_text("bytecode")
    
    # Run the tool
    result = await generate_directory_overview(str(tmp_path))
    
    # Debug: print the summaries to see what's happening
    print("\n=== Generated Summaries ===")
    for summary in result.get("summaries", []):
        print(f"File: {summary.get('file_path', 'Unknown')}")
        print(f"  Functions: {summary.get('key_functions', [])}")
        print(f"  Classes: {summary.get('key_classes', [])}")
    print("===========================\n")
    
    # Verify the result structure
    assert "error" not in result, f"Unexpected error: {result.get('error')}"
    assert "overall_summary" in result, "Should have an overall summary"
    assert "main_components" in result, "Should identify main components"
    assert "summaries" in result, "Should have file summaries"
    
    # Verify content
    assert result["overall_summary"], "Overall summary should not be empty"
    assert len(result["summaries"]) >= 3, "Should summarize at least 3 files (main.py, utils.py, test_main.py)"
    
    # Check that main.py was summarized
    main_summary = next((s for s in result["summaries"] if "main.py" in s["file_path"] and "src" in s["file_path"]), None)
    assert main_summary is not None, "main.py should be summarized"
    assert "summary" in main_summary
    assert "key_functions" in main_summary
    # Either "main" or contains "main" in one of the function names
    assert any("main" in func.lower() for func in main_summary["key_functions"]), f"Should identify a main function, but found: {main_summary['key_functions']}"
    
    # Check that utils.py was summarized
    utils_summary = next((s for s in result["summaries"] if "utils.py" in s["file_path"]), None)
    assert utils_summary is not None, "utils.py should be summarized"
    assert "Logger" in utils_summary.get("key_classes", []), "Should identify the Logger class"
    assert "format_date" in utils_summary.get("key_functions", []), "Should identify format_date function"
    
    # Verify that __pycache__ files were ignored
    pycache_summary = next((s for s in result["summaries"] if "__pycache__" in s["file_path"]), None)
    assert pycache_summary is None, "__pycache__ files should be ignored"
    
    print(f"\nOverall Summary: {result['overall_summary']}")
    print(f"Main Components: {result['main_components']}")
    print(f"Number of files summarized: {len(result['summaries'])}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_generate_directory_overview_handles_read_errors(tmp_path):
    """
    Integration test: Verify the tool handles file read errors gracefully
    """
    # Create a file with restricted permissions
    restricted_file = tmp_path / "restricted.py"
    restricted_file.write_text("secret code")
    restricted_file.chmod(0o000)  # No read permissions
    
    # Create a normal file
    (tmp_path / "normal.py").write_text("def hello(): pass")
    
    try:
        result = await generate_directory_overview(str(tmp_path))
        
        # Should still get results
        assert "error" not in result
        assert "summaries" in result
        
        # Check that the error was handled
        restricted_summary = next((s for s in result["summaries"] if "restricted.py" in s["file_path"]), None)
        if restricted_summary:
            assert "ERROR" in restricted_summary["summary"] or not restricted_summary["summary"]
            
    finally:
        # Restore permissions for cleanup
        restricted_file.chmod(0o644)