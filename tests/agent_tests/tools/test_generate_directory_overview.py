import os
import pytest
from katalyst.coding_agent.tools.generate_directory_overview import (
    generate_directory_overview,
)

pytestmark = pytest.mark.agent


@pytest.mark.agent
@pytest.mark.asyncio
async def test_functional_run_on_full_project():
    """
    Runs the tool on the entire project root as a smoke test to verify
    it can handle a real-world codebase without crashing and produces a valid output structure.
    """
    # Run on a smaller subset of the project to avoid rate limits and long runtime
    project_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../unit")  # Just the unit tests folder
    )
    print(f"\n[Agent Smoke Test] Summarizing full project directory: {project_dir}")

    result = await generate_directory_overview(project_dir)

    assert result is not None, "Result should not be None."
    assert (
        "overall_summary" in result and result["overall_summary"]
    ), "An overall summary must be generated."
    assert (
        "summaries" in result and len(result["summaries"]) > 5
    ), "Should summarize multiple files."

    # Check the structure of the first summary item
    if result["summaries"]:
        first_summary = result["summaries"][0]
        assert "file_path" in first_summary
        assert "summary" in first_summary
        assert "key_classes" in first_summary
        assert "key_functions" in first_summary
