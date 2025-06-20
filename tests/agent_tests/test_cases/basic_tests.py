import pytest
import json
from pathlib import Path
from tests.agent_tests.test_framework import KatalystTestCase, KatalystTestRunner
from tests.agent_tests.test_rubric import KatalystCodingRubric

pytestmark = pytest.mark.agent

runner = KatalystTestRunner()


def test_read_readme_first_lines():
    case = KatalystTestCase(
        name="read_readme_first_lines",
        task="read the first 5 lines of readme and tell me the first python command in that",
        auto_approve=True,
        llm_rubric=KatalystCodingRubric(
            code_is_logically_correct=True,
            no_unnecessary_files_created=True,
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


def test_create_math_project():
    case = KatalystTestCase(
        name="create_math_project",
        task="Create a folder 'mytest' with add.py, multiply.py, divide.py (each with a function), and main.py that calls all three.",
        auto_approve=True,
        llm_rubric=KatalystCodingRubric(
            all_required_files_created=True,
            code_is_complete=True,
            code_is_logically_correct=True,
            no_unnecessary_files_created=True,
            has_sufficient_comments_and_docstrings=True,
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


def test_color_preference():
    case = KatalystTestCase(
        name="color_preference",
        task="Ask me for my favorite color with suggestions 'red', 'green', 'blue'. Then tell me my choice using attempt_completion.",
        auto_approve=False,  # Requires user interaction
        llm_rubric=KatalystCodingRubric(
            code_is_logically_correct=True,
            no_unnecessary_files_created=True,
            custom_checks=[
                "The agent correctly used request_user_input and attempt_completion tools"
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


def test_file_operations():
    case = KatalystTestCase(
        name="file_operations",
        task="List all files in the current directory. Then, ask me for a filename and content, and write that to the specified file. Only proceed if I confirm.",
        auto_approve=False,  # Requires user interaction
        llm_rubric=KatalystCodingRubric(
            code_is_logically_correct=True,
            no_unnecessary_files_created=True,
            custom_checks=[
                "The agent correctly used list_files tool",
                "The agent properly handled user interaction for file creation",
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


def test_todo_plan():
    case = KatalystTestCase(
        name="todo_plan",
        task="Draft a plan for a simple to-do list application and save it as todo_plan.md. Ask me if I want to include user authentication in the plan.",
        auto_approve=False,  # Requires user interaction
        llm_rubric=KatalystCodingRubric(
            all_required_files_created=True,
            code_is_logically_correct=True,
            no_unnecessary_files_created=True,
            custom_checks=[
                "The agent created a well-structured markdown plan",
                "The agent properly handled user input about authentication",
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


def test_project_documentation():
    case = KatalystTestCase(
        name="project_documentation",
        task="Understand the current project structure and ask me what I want to document first. Then, create a basic test_plan.md with a title 'Project Plan'",
        auto_approve=False,  # Requires user interaction
        llm_rubric=KatalystCodingRubric(
            all_required_files_created=True,
            code_is_logically_correct=True,
            no_unnecessary_files_created=True,
            custom_checks=[
                "The agent analyzed the project structure correctly",
                "The agent created a properly formatted markdown document",
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
