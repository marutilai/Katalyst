import pytest
from tests.e2e.test_framework import KatalystTestCase, KatalystTestRunner
from tests.e2e.test_rubric import KatalystCodingRubric
from tests.e2e.test_utils import run_test_with_report

pytestmark = pytest.mark.e2e

runner = KatalystTestRunner()


def test_list_directory_contents():
    case = KatalystTestCase(
        name="list_directory_contents",
        task="List all files and directories in the current directory. Then, ask me which directory I'd like to explore further.",
        auto_approve=False,  # Requires user interaction
        llm_rubric=KatalystCodingRubric(
            code_is_logically_correct=True,
            no_unnecessary_files_created=True,
            custom_checks=[
                "The agent correctly listed directory contents",
                "The agent properly handled the follow-up question about directory exploration",
            ],
        ),
    )
    run_test_with_report(case, runner)


def test_check_python_version():
    case = KatalystTestCase(
        name="check_python_version",
        task="Check the Python version and tell me if it's Python 3.8 or higher. Then, ask me if I want to see the full Python version information.",
        auto_approve=False,  # Requires user interaction
        llm_rubric=KatalystCodingRubric(
            code_is_logically_correct=True,
            no_unnecessary_files_created=True,
            custom_checks=[
                "The agent correctly checked Python version",
                "The agent properly handled the follow-up question about version details",
            ],
        ),
    )
    run_test_with_report(case, runner)


def test_create_and_run_script():
    case = KatalystTestCase(
        name="create_and_run_script",
        task="Create a simple Python script called 'hello.py' that prints 'Hello, World!'. Then, run this script and show me the output. Finally, ask me if I want to modify the script to print a different message.",
        auto_approve=False,  # Requires user interaction
        llm_rubric=KatalystCodingRubric(
            all_required_files_created=True,
            code_is_logically_correct=True,
            no_unnecessary_files_created=True,
            custom_checks=[
                "The agent correctly created and executed the Python script",
                "The agent properly handled the follow-up question about script modification",
            ],
        ),
    )
    run_test_with_report(case, runner)
