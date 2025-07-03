#!/usr/bin/env python3
"""
Test script for the /init command to verify it generates complete KATALYST.md
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from katalyst.app.cli.commands import handle_init_command
from katalyst.katalyst_core.graph import build_compiled_graph
from katalyst.katalyst_core.utils.logger import get_logger
from langgraph.checkpoint.memory import MemorySaver

logger = get_logger()


def test_init_command():
    """Test the /init command in a temporary directory"""
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy the current project to temp dir for testing
        project_root = Path(__file__).parent.parent.parent.parent
        test_project_dir = Path(temp_dir) / "test_katalyst"
        
        # Copy only essential directories
        shutil.copytree(project_root / "src", test_project_dir / "src")
        shutil.copytree(project_root / "tests", test_project_dir / "tests")
        shutil.copy(project_root / "pyproject.toml", test_project_dir / "pyproject.toml")
        shutil.copy(project_root / "README.md", test_project_dir / "README.md")
        
        # Change to test directory
        original_cwd = os.getcwd()
        os.chdir(test_project_dir)
        
        try:
            print(f"Testing /init command in: {test_project_dir}")
            
            # Create graph and config (matching main.py)
            checkpointer = MemorySaver()
            graph = build_compiled_graph().with_config(checkpointer=checkpointer)
            config = {
                "configurable": {"thread_id": "test-init-thread"},
                "recursion_limit": int(os.getenv("KATALYST_RECURSION_LIMIT", 250)),
            }
            
            # Run the init command
            handle_init_command(graph, config)
            
            # Check if KATALYST.md was created
            katalyst_md = test_project_dir / "KATALYST.md"
            assert katalyst_md.exists(), "KATALYST.md was not created"
            
            # Check file size and content
            content = katalyst_md.read_text()
            lines = content.split('\n')
            assert len(content) > 0, "KATALYST.md is empty"
            assert len(lines) > 100, f"KATALYST.md is too short ({len(lines)} lines)"
            
            # Check for required sections
            required_sections = [
                "Project Overview",
                "Setup and Installation",
                "Test Commands",
                "Architecture Overview",
                "Key Components",
                "Project Layout",
                "Technologies Used",
                "Main Entry Point",
                "Environment Variables",
                "Example Usage"
            ]
            
            missing_sections = []
            for section in required_sections:
                if section not in content:
                    missing_sections.append(section)
            
            assert not missing_sections, f"Missing sections: {', '.join(missing_sections)}"
            
            # Check for placeholders
            assert not ("..." in content and "(previous sections)" in content), "Found placeholders in the document"
            
            # Check for ASCII tree
            assert "├──" in content or "└──" in content, "No ASCII tree structure found in Project Layout"
            
            # Print first 50 lines as preview (for debugging purposes)
            print("\n--- First 50 lines of KATALYST.md ---")
            for i, line in enumerate(lines[:50]):
                print(f"{i+1:3}: {line}")
            
            # Check for any temporary files
            temp_files = []
            for file in test_project_dir.glob("*.md"):
                if file.name != "KATALYST.md" and file.name != "README.md":
                    temp_files.append(file.name)
            
            assert not temp_files, f"Found temporary files that should have been deleted: {temp_files}"
                
        finally:
            # Restore original directory
            os.chdir(original_cwd)


if __name__ == "__main__":
    print("Testing /init command...\n")
    try:
        test_init_command()
        print("\n✅ All tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        raise