import pytest
from tests.agent_tests.test_framework import KatalystTestCase, KatalystTestRunner
from tests.agent_tests.test_rubric import KatalystCodingRubric

pytestmark = pytest.mark.agent

runner = KatalystTestRunner()


def test_change_logger_name():
    case = KatalystTestCase(
        name="change_logger_name",
        task="Read the file katalyst/coding_agent/utils/logger.py. Then, propose a diff to change the _LOGGER_NAME from 'coding_agent' to 'katalyst_logger'. Apply this diff only after my confirmation. Ensure the syntax is still valid after the change.",
        expected_output="diff",
        auto_approve=False,  # Requires user interaction
    )
    result = runner.run_test(case)
    assert result.success


def test_add_agent_version():
    case = KatalystTestCase(
        name="add_agent_version",
        task="In katalyst/coding_agent/main.py, inside the repl function's else block where initial_state is created, add a new key-value pair: 'agent_version': '1.0.0'. Use the apply_source_code_diff tool. Show me the proposed diff and apply it after my confirmation.",
        expected_output="agent_version",
        auto_approve=False,  # Requires user interaction
    )
    result = runner.run_test(case)
    assert result.success
