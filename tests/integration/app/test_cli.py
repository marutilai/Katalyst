import subprocess
import shutil
import pytest
from unittest.mock import patch, MagicMock
from katalyst.app.cli.commands import handle_init_command, handle_provider_command

"""
ToDo: Add tests for the CLI

- A test for the /init command, for instance, might need to touch the file system to check if KATALYST.md is created. This is an integration test, but it could still be written to mock the final graph.invoke call, so it doesn't need a real LLM.
"""

pytestmark = pytest.mark.integration  # Mark all tests in this file as integration tests


def test_cli_help():
    cli_path = shutil.which("katalyst")
    if cli_path is None:
        raise RuntimeError("katalyst CLI not found in PATH")
    result = subprocess.run([cli_path, "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert (
        "Usage" in result.stdout
        or "usage" in result.stdout
        or "KATALYST" in result.stdout
    )
