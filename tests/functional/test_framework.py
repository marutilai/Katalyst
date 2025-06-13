from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from pathlib import Path
import json
import time
from datetime import datetime
from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.graph import build_compiled_graph
from katalyst.katalyst_core.utils.logger import get_logger


@dataclass
class KatalystTestCase:
    """Represents a single test case for the Katalyst agent."""

    name: str
    task: str
    expected_output: Optional[str] = None
    expected_error: Optional[str] = None
    expected_files: Optional[Dict[str, str]] = None  # path -> expected content
    expected_commands: Optional[List[str]] = None
    timeout: int = 30
    auto_approve: bool = False
    user_inputs: Optional[List[str]] = None  # List of inputs to simulate user responses


@dataclass
class KatalystTestResult:
    """Represents the result of executing a test case."""

    test_case: KatalystTestCase
    success: bool
    actual_output: Optional[str] = None
    actual_error: Optional[str] = None
    execution_time: float = 0.0
    error_messages: List[str] = None
    created_files: Dict[str, str] = None  # path -> actual content
    executed_commands: List[str] = None

    def __post_init__(self):
        if self.error_messages is None:
            self.error_messages = []
        if self.created_files is None:
            self.created_files = {}
        if self.executed_commands is None:
            self.executed_commands = []


class KatalystTestRunner:
    """Runs test cases and generates reports."""

    def __init__(self, auto_approve: bool = False):
        self.logger = get_logger()
        self.auto_approve = auto_approve
        self.user_input_index = 0
        self.user_inputs = []

    def _validate_output(
        self, test_case: KatalystTestCase, final_state: KatalystState
    ) -> List[str]:
        """Validate the test output against expectations."""
        errors = []

        # Check expected output
        if test_case.expected_output:
            if (
                not final_state.response
                or test_case.expected_output not in final_state.response
            ):
                errors.append(
                    f"Expected output '{test_case.expected_output}' not found in response: {final_state.response}"
                )

        # Check expected error
        if test_case.expected_error:
            if (
                not final_state.error_message
                or test_case.expected_error not in final_state.error_message
            ):
                errors.append(
                    f"Expected error '{test_case.expected_error}' not found in error: {final_state.error_message}"
                )

        # Check expected files
        if test_case.expected_files:
            for file_path, expected_content in test_case.expected_files.items():
                if not Path(file_path).exists():
                    errors.append(f"Expected file {file_path} was not created")
                else:
                    with open(file_path, "r") as f:
                        actual_content = f.read()
                        if expected_content not in actual_content:
                            errors.append(
                                f"Expected content '{expected_content}' not found in {file_path}"
                            )

        return errors

    def _simulate_user_input(self, prompt: str) -> str:
        """Simulate user input for the current test case."""
        if self.user_input_index < len(self.user_inputs):
            response = self.user_inputs[self.user_input_index]
            self.user_input_index += 1
            self.logger.info(f"Simulated user input: {response}")
            return response
        return ""

    def run_test(self, test_case: KatalystTestCase) -> KatalystTestResult:
        """Run a single test case and return its result."""
        start_time = time.time()
        self.user_input_index = 0
        self.user_inputs = test_case.user_inputs or []

        result = KatalystTestResult(test_case=test_case, success=False)

        try:
            # Initialize state
            state = KatalystState(
                task=test_case.task, auto_approve=test_case.auto_approve
            )

            # Run the graph
            app = build_compiled_graph()
            final_state = app.invoke(state)

            # Record execution details
            result.actual_output = final_state.response
            result.actual_error = final_state.error_message
            result.execution_time = time.time() - start_time

            # Validate results
            validation_errors = self._validate_output(test_case, final_state)
            if validation_errors:
                result.error_messages.extend(validation_errors)
                result.success = False
            else:
                result.success = True

            # Record created files
            if test_case.expected_files:
                for file_path in test_case.expected_files.keys():
                    if Path(file_path).exists():
                        with open(file_path, "r") as f:
                            result.created_files[file_path] = f.read()

        except Exception as e:
            result.success = False
            result.actual_error = str(e)
            result.error_messages.append(f"Test execution failed: {str(e)}")

        result.execution_time = time.time() - start_time
        return result

    def run_tests(self, test_cases: List[KatalystTestCase]) -> List[KatalystTestResult]:
        """Run multiple test cases and return their results."""
        results = []
        for test_case in test_cases:
            self.logger.info(f"Running test: {test_case.name}")
            result = self.run_test(test_case)
            results.append(result)
            status = "passed" if result.success else "failed"
            self.logger.info(f"Test {test_case.name} {status}")
            if not result.success and result.error_messages:
                self.logger.error(f"Errors: {result.error_messages}")
        return results

    def generate_report(
        self, results: List[KatalystTestResult], output_file: str = "test_report.json"
    ):
        """Generate a JSON report of test results."""
        report = {
            "summary": {
                "total": len(results),
                "passed": sum(1 for r in results if r.success),
                "failed": sum(1 for r in results if not r.success),
                "total_time": sum(r.execution_time for r in results),
            },
            "results": [
                {
                    "name": r.test_case.name,
                    "success": r.success,
                    "execution_time": r.execution_time,
                    "error_messages": r.error_messages,
                    "expected_output": r.test_case.expected_output,
                    "actual_output": r.actual_output,
                    "expected_error": r.test_case.expected_error,
                    "actual_error": r.actual_error,
                    "created_files": r.created_files,
                    "executed_commands": r.executed_commands,
                }
                for r in results
            ],
        }

        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)

        self.logger.info(f"Test report written to {output_file}")


# Actual pytest test functions
def test_test_case_creation():
    """Test that KatalystTestCase can be created with required fields."""
    test_case = KatalystTestCase(
        name="test1",
        task="Test task",
        expected_output="Expected output",
        user_inputs=["yes", "no"],
    )
    assert test_case.name == "test1"
    assert test_case.task == "Test task"
    assert test_case.expected_output == "Expected output"
    assert test_case.user_inputs == ["yes", "no"]


def test_test_result_creation():
    """Test that KatalystTestResult can be created with required fields."""
    test_case = KatalystTestCase(name="test1", task="Test task")
    result = KatalystTestResult(
        test_case=test_case, success=True, actual_output="Test passed"
    )
    assert result.test_case == test_case
    assert result.success is True
    assert result.actual_output == "Test passed"
    assert isinstance(result.error_messages, list)
    assert isinstance(result.created_files, dict)
    assert isinstance(result.executed_commands, list)


def test_test_runner_initialization():
    """Test that KatalystTestRunner can be initialized."""
    runner = KatalystTestRunner(auto_approve=True)
    assert runner.auto_approve is True
    assert runner.logger is not None
