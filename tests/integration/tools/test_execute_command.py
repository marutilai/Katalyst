import pytest
from katalyst.coding_agent.tools.execute_command import execute_command
import sys

pytestmark = pytest.mark.integration


def test_execute_command_success():
    # Use a cross-platform command
    cmd = "echo hello" if sys.platform != "win32" else "echo hello"
    result = execute_command(cmd, auto_approve=True)
    assert "success" in result and "hello" in result


def test_execute_command_not_found():
    result = execute_command("nonexistent_command_xyz", auto_approve=True)
    assert "error" in result or "not found" in result.lower()
