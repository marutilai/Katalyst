import pytest
import json
from pathlib import Path
from tests.agent_tests.test_framework import KatalystTestCase, KatalystTestRunner
from tests.agent_tests.test_rubric import KatalystCodingRubric

pytestmark = pytest.mark.agent

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
    result = runner.run_test(case)

    # Generate detailed report for this test
    report_file = f"test_report_{case.name}.json"
    runner.generate_report([result], report_file)

    # Assert success and check that report was generated
    assert result.success, f"Test failed: {result.error_messages}"
    assert Path(report_file).exists(), f"Report file {report_file} was not generated"

    # Load and verify report structure
    with open(report_file, "r") as f:
        report = json.load(f)

    assert report["summary"]["total"] == 1
    assert report["summary"]["passed"] == 1 if result.success else 0
    assert len(report["results"]) == 1
    assert report["results"][0]["name"] == case.name
    assert report["results"][0]["success"] == result.success

    # Check that LLM evaluation is present if test passed
    if result.success and result.llm_evaluation:
        assert report["results"][0]["llm_evaluation"] is not None
        assert "overall_passed" in report["results"][0]["llm_evaluation"]
        assert "reasoning_by_criterion" in report["results"][0]["llm_evaluation"]


# def test_analyze_utils_directory():
#     case = KatalystTestCase(
#         name="analyze_utils_directory",
#         task="Analyze the katalyst/katalyst_core/utils directory. For each Python file, list its function definitions. Then ask me which function from environment.py I'd like to understand better.",
#         auto_approve=False,  # Requires user interaction
#         llm_rubric=KatalystCodingRubric(
#             code_is_logically_correct=True,
#             no_unnecessary_files_created=True,
#             custom_checks=[
#                 "The agent correctly analyzed directory contents",
#                 "The agent properly handled the follow-up question about function choice",
#             ],
#         ),
#     )
#     result = runner.run_test(case)

#     # Generate detailed report for this test
#     report_file = f"test_report_{case.name}.json"
#     runner.generate_report([result], report_file)

#     # Assert success and check that report was generated
#     assert result.success, f"Test failed: {result.error_messages}"
#     assert Path(report_file).exists(), f"Report file {report_file} was not generated"

#     # Load and verify report structure
#     with open(report_file, "r") as f:
#         report = json.load(f)

#     assert report["summary"]["total"] == 1
#     assert report["summary"]["passed"] == 1 if result.success else 0
#     assert len(report["results"]) == 1
#     assert report["results"][0]["name"] == case.name
#     assert report["results"][0]["success"] == result.success

#     # Check that LLM evaluation is present if test passed
#     if result.success and result.llm_evaluation:
#         assert report["results"][0]["llm_evaluation"] is not None
#         assert "overall_passed" in report["results"][0]["llm_evaluation"]
#         assert "reasoning_by_criterion" in report["results"][0]["llm_evaluation"]
