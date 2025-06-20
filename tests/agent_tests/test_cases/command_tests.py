import pytest
from tests.agent_tests.test_framework import KatalystTestCase, KatalystTestRunner
from tests.agent_tests.test_rubric import KatalystCodingRubric

pytestmark = pytest.mark.agent

runner = KatalystTestRunner()


def test_list_and_create_file():
    case = KatalystTestCase(
        name="list_and_create_file",
        task="List all files in the current directory using a shell command. Then, create a new file named test_output.txt containing the text 'Hello from Katalyst' using the write_to_file tool.",
        auto_approve=True,
        llm_rubric=KatalystCodingRubric(
            all_required_files_created=True,
            code_is_logically_correct=True,
            no_unnecessary_files_created=True,
            validation_command_was_run=True,
        ),
    )
    result = runner.run_test(case)
    assert result.success
