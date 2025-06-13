import os
import pytest
from katalyst.coding_agent.tools.generate_directory_overview import (
    generate_directory_overview,
)


@pytest.mark.asyncio
async def test_generate_directory_overview_functional():
    """
    Functional test: Run generate_directory_overview on a real project directory and print the results for manual review.
    """
    # Use the root of the current project as the test directory
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    print(f"\n[Functional Test] Summarizing project directory: {project_dir}")

    result = await generate_directory_overview(project_dir)

    print("\n--- FUNCTIONAL TEST: generate_directory_overview ---")
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
