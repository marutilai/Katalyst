import pytest
import json
from pathlib import Path
from tests.e2e.test_framework import KatalystTestCase, KatalystTestRunner
from tests.e2e.test_rubric import KatalystCodingRubric
from tests.e2e.test_utils import run_test_with_report

pytestmark = pytest.mark.e2e

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


def test_build_simple_web_app():
    case = KatalystTestCase(
        name="build_simple_web_app",
        task="Create a simple Flask web application with the following structure: app.py (main Flask app), templates/index.html (basic HTML template), and static/style.css (basic CSS). The app should have a route that displays 'Hello from Katalyst' and ask me what additional features I'd like to add.",
        auto_approve=False,  # Requires user interaction
        llm_rubric=KatalystCodingRubric(
            all_required_files_created=True,
            code_is_complete=True,
            code_is_logically_correct=True,
            no_unnecessary_files_created=True,
            has_sufficient_comments_and_docstrings=True,
            custom_checks=[
                "The agent created a functional Flask application structure",
                "The agent properly handled the follow-up question about additional features",
            ],
        ),
    )
    run_test_with_report(case, runner)


def test_create_data_analysis_script():
    case = KatalystTestCase(
        name="create_data_analysis_script",
        task="Create a Python script that performs basic data analysis. The script should: 1) Generate sample data (random numbers), 2) Calculate basic statistics (mean, median, std), 3) Create a simple plot, 4) Save results to a file. Ask me what type of data I'd like to analyze.",
        auto_approve=False,  # Requires user interaction
        llm_rubric=KatalystCodingRubric(
            all_required_files_created=True,
            code_is_complete=True,
            code_is_logically_correct=True,
            no_unnecessary_files_created=True,
            has_sufficient_comments_and_docstrings=True,
            custom_checks=[
                "The agent created a functional data analysis script",
                "The agent properly handled the follow-up question about data type",
            ],
        ),
    )
    run_test_with_report(case, runner)


def test_build_api_with_documentation():
    case = KatalystTestCase(
        name="build_api_with_documentation",
        task="Create a simple REST API using FastAPI with the following endpoints: GET /items (list items), POST /items (add item), GET /items/{item_id} (get specific item). Include proper documentation, error handling, and ask me what additional endpoints I'd like to add.",
        auto_approve=False,  # Requires user interaction
        llm_rubric=KatalystCodingRubric(
            all_required_files_created=True,
            code_is_complete=True,
            code_is_logically_correct=True,
            no_unnecessary_files_created=True,
            has_sufficient_comments_and_docstrings=True,
            custom_checks=[
                "The agent created a functional FastAPI application",
                "The agent included proper documentation and error handling",
                "The agent properly handled the follow-up question about additional endpoints",
            ],
        ),
    )
    run_test_with_report(case, runner)
