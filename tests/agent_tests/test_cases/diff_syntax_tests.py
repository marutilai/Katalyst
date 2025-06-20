import pytest
from tests.agent_tests.test_framework import KatalystTestCase, KatalystTestRunner
from tests.agent_tests.test_rubric import KatalystCodingRubric
from tests.agent_tests.test_utils import run_test_with_report

pytestmark = pytest.mark.agent

runner = KatalystTestRunner()


def test_apply_diff_to_file():
    case = KatalystTestCase(
        name="apply_diff_to_file",
        task="Create a file called 'test_diff.txt' with the content 'Hello World'. Then, apply a diff to change 'Hello' to 'Goodbye' and 'World' to 'Universe'.",
        auto_approve=True,
        llm_rubric=KatalystCodingRubric(
            all_required_files_created=True,
            code_is_logically_correct=True,
            no_unnecessary_files_created=True,
            custom_checks=[
                "The agent correctly applied the diff to modify the file content"
            ],
        ),
    )
    run_test_with_report(case, runner)


def test_syntax_check_python():
    case = KatalystTestCase(
        name="syntax_check_python",
        task="Create a Python file called 'syntax_test.py' with a function that has a syntax error (missing colon after def). Then, check the syntax of this file and report the error.",
        auto_approve=True,
        llm_rubric=KatalystCodingRubric(
            all_required_files_created=True,
            code_is_logically_correct=True,
            no_unnecessary_files_created=True,
            custom_checks=[
                "The agent correctly identified and reported the syntax error"
            ],
        ),
    )
    run_test_with_report(case, runner)


def test_change_logger_name():
    case = KatalystTestCase(
        name="change_logger_name",
        task="Read the content of katalyst/katalyst_core/utils/logger.py and then apply a diff to change the logger name from 'katalyst' to 'katalyst_agent'.",
        auto_approve=True,
        llm_rubric=KatalystCodingRubric(
            code_is_logically_correct=True,
            no_unnecessary_files_created=True,
            custom_checks=["The agent correctly read the file and applied the diff"],
        ),
    )
    run_test_with_report(case, runner)


def test_add_agent_version():
    case = KatalystTestCase(
        name="add_agent_version",
        task="In katalyst/coding_agent/main.py, inside the repl function's else block where initial_state is created, add a new key-value pair: 'agent_version': '1.0.0'. Use the apply_source_code_diff tool. Show me the proposed diff and apply it after my confirmation.",
        expected_output="agent_version",
        auto_approve=False,  # Requires user interaction
    )
    result = runner.run_test(case)
    assert result.success
