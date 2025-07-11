import pytest
from tests.e2e.test_framework import KatalystTestCase, KatalystTestRunner
from tests.e2e.test_rubric import KatalystCodingRubric
from tests.e2e.test_utils import run_test_with_report

pytestmark = pytest.mark.e2e

runner = KatalystTestRunner()


def test_search_katalyst_in_md():
    case = KatalystTestCase(
        name="search_katalyst_in_md",
        task="Search for all occurrences of the word 'Katalyst' in any .md files in the current directory and its subdirectories. Then, read the first 5 lines of README.md.",
        auto_approve=True,
        llm_rubric=KatalystCodingRubric(
            code_is_logically_correct=True,
            no_unnecessary_files_created=True,
            custom_checks=["The agent used appropriate search and read tools"],
        ),
    )
    run_test_with_report(case, runner)


def test_find_python_imports():
    case = KatalystTestCase(
        name="find_python_imports",
        task="Find all Python files (.py) in the katalyst/coding_agent/nodes directory that import the KatalystState. For each match, show me the line number and the matching line. Then, ask me if I want to see the full content of katalyst/coding_agent/nodes/invoke_llm.py.",
        auto_approve=False,  # Requires user interaction
        llm_rubric=KatalystCodingRubric(
            code_is_logically_correct=True,
            no_unnecessary_files_created=True,
            custom_checks=[
                "The agent used appropriate search tools to find imports",
                "The agent properly handled the follow-up question about file content",
            ],
        ),
    )
    run_test_with_report(case, runner)
