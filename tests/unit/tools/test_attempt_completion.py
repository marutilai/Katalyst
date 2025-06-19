import pytest
from unittest.mock import patch, AsyncMock
from katalyst.coding_agent.tools.attempt_completion import attempt_completion

pytestmark = pytest.mark.unit  # Mark all tests in this file as unit tests


def test_attempt_completion_success():
    result = attempt_completion("Task complete!")
    assert "success" in result and "Task complete!" in result


def test_attempt_completion_missing():
    result = attempt_completion("")
    assert "error" in result or "No valid" in result
