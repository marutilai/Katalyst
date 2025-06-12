import os
import pytest
from src.coding_agent.tools.summarize_code_structure import summarize_code_structure


@pytest.mark.asyncio
async def test_summarize_code_structure_functional():
    """
    Functional test: Run summarize_code_structure on a real project directory and print the results for manual review.
    """
    # Use the root of the current project as the test directory
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
    print(f"\n[Functional Test] Summarizing project directory: {project_dir}")

    result = await summarize_code_structure(project_dir)

    print("\n--- FUNCTIONAL TEST: summarize_code_structure ---")
    print("Overall Summary:")
    print(result.get("overall_summary", "<none>"))
    print("\nMain Components:")
    print(result.get("main_components", []))
    print("\nFile Summaries (first 10):")
    for summary in result.get("summaries", [])[:10]:
        print(f"- {summary['file_path']}: {summary['summary']}")
    if len(result.get("summaries", [])) > 10:
        print(f"... ({len(result['summaries']) - 10} more files not shown) ...")

    # This is a functional test for manual review, so we do not assert on the output.
