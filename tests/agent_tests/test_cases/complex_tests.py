import pytest
from tests.agent_tests.test_framework import KatalystTestCase, KatalystTestRunner
from tests.agent_tests.test_rubric import KatalystCodingRubric

pytestmark = pytest.mark.agent

runner = KatalystTestRunner()


def test_refactor_logger_function():
    case = KatalystTestCase(
        name="refactor_logger_function",
        task="I want to refactor the get_logger function in katalyst/coding_agent/utils/logger.py. First, search for all files in katalyst/coding_agent that import get_logger from this path. Then, read the get_logger function itself. After that, ask me for the new desired name for this function. Finally, use apply_source_code_diff to rename the function.",
        expected_output="get_logger",
        auto_approve=False,  # Requires user interaction
    )
    result = runner.run_test(case)
    assert result.success


def test_create_and_run_sandbox():
    case = KatalystTestCase(
        name="create_and_run_sandbox",
        task="Create a new Python file katalyst/coding_agent/experiments/sandbox.py. Inside this file, write a simple function called greet(name: str) -> str that returns f'Hello, {name}!'. After writing the file, execute it with the command python katalyst/coding_agent/experiments/sandbox.py if it had a main block to print a greeting (modify it to do so if needed, then execute).",
        expected_files={"katalyst/coding_agent/experiments/sandbox.py": "def greet"},
    )
    result = runner.run_test(case)
    assert result.success
