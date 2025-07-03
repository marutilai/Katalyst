import pytest
from tests.e2e.test_framework import KatalystTestCase, KatalystTestRunner
from tests.e2e.test_rubric import KatalystCodingRubric
from tests.e2e.test_utils import run_test_with_report

pytestmark = pytest.mark.e2e

runner = KatalystTestRunner()


def test_list_write_file_definitions():
    case = KatalystTestCase(
        name="list_write_file_definitions",
        task="List all function and class definitions in katalyst.coding_agent.tools/write_to_file.py. Then, read the content of the write_to_file function itself from that file.",
        auto_approve=True,
        llm_rubric=KatalystCodingRubric(
            code_is_logically_correct=True,
            no_unnecessary_files_created=True,
            custom_checks=[
                "The agent correctly used code analysis tools to list definitions"
            ],
        ),
    )
    run_test_with_report(case, runner)


def test_analyze_utils_directory():
    case = KatalystTestCase(
        name="analyze_utils_directory",
        task="Analyze the katalyst/katalyst_core/utils directory. For each Python file, list its function definitions. Then ask me which function from environment.py I'd like to understand better.",
        auto_approve=False,  # Requires user interaction
        llm_rubric=KatalystCodingRubric(
            code_is_logically_correct=True,
            no_unnecessary_files_created=True,
            custom_checks=[
                "The agent correctly analyzed directory contents",
                "The agent properly handled the follow-up question about function choice",
            ],
        ),
    )
    run_test_with_report(case, runner)
