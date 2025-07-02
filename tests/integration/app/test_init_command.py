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
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

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
        project_root = Path(__file__).parent.parent
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
            if katalyst_md.exists():
                print("\n✅ KATALYST.md was created successfully!")
                
                # Check file size and content
                content = katalyst_md.read_text()
                lines = content.split('\n')
                print(f"📄 File size: {len(content)} characters")
                print(f"📄 Line count: {len(lines)} lines")
                
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
                
                if missing_sections:
                    print(f"\n⚠️  Missing sections: {', '.join(missing_sections)}")
                else:
                    print("\n✅ All required sections are present!")
                
                # Check for placeholders
                if "..." in content and "(previous sections)" in content:
                    print("\n❌ Found placeholders in the document!")
                else:
                    print("✅ No placeholders found - document appears complete!")
                
                # Check for ASCII tree
                if "├──" in content or "└──" in content:
                    print("✅ ASCII tree structure found in Project Layout!")
                else:
                    print("⚠️  No ASCII tree structure found in Project Layout")
                
                # Print first 50 lines as preview
                print("\n--- First 50 lines of KATALYST.md ---")
                for i, line in enumerate(lines[:50]):
                    print(f"{i+1:3}: {line}")
                
                # Check for any temporary files
                temp_files = []
                for file in test_project_dir.glob("*.md"):
                    if file.name != "KATALYST.md" and file.name != "README.md":
                        temp_files.append(file.name)
                
                if temp_files:
                    print(f"\n⚠️  Found temporary files that should have been deleted: {temp_files}")
                else:
                    print("\n✅ No temporary files found - cleanup was successful!")
                    
            else:
                print("\n❌ KATALYST.md was NOT created!")
                
        finally:
            # Restore original directory
            os.chdir(original_cwd)


if __name__ == "__main__":
    print("Testing /init command...\n")
    test_init_command()