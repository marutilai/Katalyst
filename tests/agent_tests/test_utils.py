import json
from pathlib import Path
from typing import List
from tests.agent_tests.test_framework import KatalystTestResult


def generate_and_validate_report(
    result: KatalystTestResult, case_name: str, runner
) -> None:
    """
    Generate a test report and validate its structure.

    Args:
        result: The test result from KatalystTestRunner
        case_name: Name of the test case
        runner: The KatalystTestRunner instance
    """
    # Generate detailed report for this test
    report_file = f"test_reports/test_report_{case_name}.json"
    runner.generate_report([result], report_file)
    print(f"\n📊 Test report written to: {report_file}")

    # Assert success and check that report was generated
    assert result.success, f"Test failed: {result.error_messages}"
    assert Path(report_file).exists(), f"Report file {report_file} was not generated"

    # Load and verify report structure
    with open(report_file, "r") as f:
        report = json.load(f)

    assert report["summary"]["total"] == 1
    assert report["summary"]["passed"] == 1 if result.success else 0
    assert len(report["results"]) == 1
    assert report["results"][0]["name"] == case_name
    assert report["results"][0]["success"] == result.success

    # Check that LLM evaluation is present if test passed
    if result.success and result.llm_evaluation:
        assert report["results"][0]["llm_evaluation"] is not None
        assert "overall_passed" in report["results"][0]["llm_evaluation"]
        assert "reasoning_by_criterion" in report["results"][0]["llm_evaluation"]


def run_test_with_report(case, runner) -> KatalystTestResult:
    """
    Run a test case and generate a report with validation.

    Args:
        case: The KatalystTestCase to run
        runner: The KatalystTestRunner instance

    Returns:
        The test result
    """
    result = runner.run_test(case)
    generate_and_validate_report(result, case.name, runner)
    return result
