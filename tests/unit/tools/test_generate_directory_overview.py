import pytest
from unittest.mock import patch, AsyncMock
from katalyst.coding_agent.tools.generate_directory_overview import (
    generate_directory_overview,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_error_on_single_file_path():
    """Unit test: a single file path should immediately return an error without calling an LLM."""
    result = await generate_directory_overview("some/file.py")
    assert "error" in result and "directory" in result["error"].lower()


@pytest.mark.asyncio
async def test_error_on_nonexistent_path():
    """Unit test: a non-existent path should fail before any LLM call."""
    result = await generate_directory_overview("path/that/does/not/exist")
    assert "error" in result and "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_error_on_empty_directory(tmp_path):
    """Unit test: an empty directory should fail before any LLM call."""
    result = await generate_directory_overview(str(tmp_path))
    assert "error" in result and "no files to summarize" in result["error"].lower()


@pytest.mark.asyncio
# We patch the 'app.ainvoke' method within the tool's module.
@patch(
    "katalyst.coding_agent.tools.generate_directory_overview.app.ainvoke",
    new_callable=AsyncMock,
)
async def test_respects_gitignore(mock_ainvoke, tmp_path):
    """
    Unit test: Verifies that gitignored files are filtered out before being passed to the internal graph.
    """
    # Arrange: Setup file structure
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "ignored.log").write_text("secret")
    (tmp_path / ".gitignore").write_text("*.log")

    # Set a dummy return value for the mocked graph invocation to prevent errors
    mock_ainvoke.return_value = {"summaries": [], "final_summary": {}}

    # Act: Run the tool. This will call our mock_ainvoke instead of the real graph.
    await generate_directory_overview(str(tmp_path))

    # Assert: Check that the mock was called, and inspect the arguments it received.
    assert (
        mock_ainvoke.called
    ), "The internal graph's ainvoke method should have been called."

    # Get the arguments passed to the mock. `call_args` is a tuple of (args, kwargs).
    # The first argument (index 0) is the `initial_state` dictionary.
    call_args, call_kwargs = mock_ainvoke.call_args
    invoked_state = call_args[0]

    # The crucial assertion: check the 'contents' list that was prepared for the graph.
    files_to_be_processed = invoked_state["contents"]

    assert any(
        "main.py" in f for f in files_to_be_processed
    ), "main.py should be in the list of files to process."
    assert not any(
        "ignored.log" in f for f in files_to_be_processed
    ), "ignored.log should have been filtered out."
