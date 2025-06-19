from enum import Enum
import os
from typing import List, Dict, Optional
from pathlib import Path
import json
import time

from pydantic import BaseModel, Field
from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.graph import build_compiled_graph
from katalyst.katalyst_core.utils.logger import get_logger


# -------- User Input Simulation Modes --------
class UserInputMode(str, Enum):
    first = "first"
    last = "last"
    custom = "custom"


class UserInputConfig(BaseModel):
    mode: UserInputMode = UserInputMode.first
    custom_response: str = "1"  # Used only if mode == custom


# -------- LLM Evaluation Result (structured) --------
class LLMEvaluationResult(BaseModel):
    passed: bool = Field(
        ..., description="True if the agent's work meets all success criteria."
    )
    reasoning: str = Field(
        ...,
        description="A step-by-step analysis of how the agent's output meets or fails each criterion.",
    )
    score: float = Field(
        ..., ge=0.0, le=1.0, description="A quality score from 0.0 to 1.0."
    )


# -------- Test Case Definition --------
class KatalystTestCase(BaseModel):
    name: str = Field(..., description="Unique name for the test case")
    task: str = Field(..., description="The task to be executed by the agent")
    llm_eval_instructions: str = Field(
        ..., description="Instructions for LLM judgment (natural language)"
    )
    llm_rubric: Optional[List[str]] = Field(
        None, description="Scoring rubric (list of criteria)"
    )
    llm_model: str = Field("gpt-4o", description="LLM model to use for evaluation")
    timeout: int = Field(60, description="Timeout in seconds")
    auto_approve: bool = Field(
        False, description="Whether to auto-approve user prompts"
    )
    user_input_config: UserInputConfig = Field(
        default_factory=UserInputConfig,
        description="Configuration for user input simulation",
    )


# -------- Test Result Structure --------
class KatalystTestResult(BaseModel):
    test_case: KatalystTestCase = Field(
        ..., description="The test case that was executed"
    )
    success: bool = Field(..., description="Whether the test passed")
    actual_output: Optional[str] = Field(
        None, description="Actual output from the agent"
    )
    execution_time: float = Field(0.0, description="Time taken to execute the test")
    error_messages: List[str] = Field(
        default_factory=list, description="List of error messages"
    )
    created_files: Dict[str, str] = Field(
        default_factory=dict, description="Files created by the agent (path -> content)"
    )
    llm_evaluation: Optional[LLMEvaluationResult] = Field(
        None, description="LLM evaluation result"
    )


# -------- LLM Prompt Builder --------
def build_llm_eval_prompt(
    test_case: KatalystTestCase, result: KatalystTestResult
) -> str:
    rubric = "\n".join(f"- {c}" for c in (test_case.llm_rubric or []))
    files = (
        json.dumps(result.created_files, indent=2) if result.created_files else "N/A"
    )
    return f"""
TASK:
{test_case.task}

OUTPUT:
{result.actual_output}

FILES CREATED:
{files}

EVALUATION RUBRIC:
{rubric}

INSTRUCTIONS:
{test_case.llm_eval_instructions}

Respond ONLY with a valid JSON in this format:
{{"passed": true/false, "score": float, "reasoning": "..."}}"""


# -------- Test Runner Core --------
class KatalystTestRunner:
    def __init__(
        self,
        auto_approve: bool = False,
        user_input_config: Optional[UserInputConfig] = None,
    ):
        self.logger = get_logger()
        self.auto_approve = auto_approve
        # Always default to picking first option unless overridden
        self.user_input_config = user_input_config or UserInputConfig()

    def _simulate_user_input(self, prompt: str) -> str:
        """Simulate user input for all test cases according to config."""
        mode = self.user_input_config.mode
        if mode == UserInputMode.first:
            self.logger.info("user_input_mode=first: selecting default answer '1'")
            return "1"
        elif mode == UserInputMode.last:
            # Try to infer number of options; fallback to '5' as example
            import re

            matches = re.findall(r"^\s*\d+\.", prompt, re.MULTILINE)
            last_option = str(len(matches)) if matches else "5"
            self.logger.info(f"user_input_mode=last: selecting answer '{last_option}'")
            return last_option
        elif mode == UserInputMode.custom:
            self.logger.info(
                f"user_input_mode=custom: selecting '{self.user_input_config.custom_response}'"
            )
            return self.user_input_config.custom_response
        else:
            raise RuntimeError("Unknown user input mode.")

    def _gather_created_files(self, initial_files: set) -> Dict[str, str]:
        """
        Collect all files created or modified by the agent for this test case.
        Only includes files that weren't present in the initial snapshot.
        """
        files = {}
        current_files = set(p.resolve() for p in Path(".").rglob("*"))
        new_and_modified_paths = current_files - initial_files

        self.logger.debug(f"Initial files count: {len(initial_files)}")
        self.logger.debug(f"Current files count: {len(current_files)}")
        self.logger.debug(f"New/modified files count: {len(new_and_modified_paths)}")

        for path in new_and_modified_paths:
            if path.is_file():
                try:
                    # Make path relative for cleaner report
                    relative_path = str(path.relative_to(Path.cwd()))
                    content = path.read_text()
                    files[relative_path] = content
                    self.logger.debug(f"Found created/modified file: {relative_path}")
                except Exception as e:
                    self.logger.debug(f"Could not read file {path}: {e}")
                    continue  # Skip unreadable/binary files

        self.logger.debug(f"Total files gathered: {len(files)}")
        return files

    def _run_llm_evaluation(
        self, test_case: KatalystTestCase, result: KatalystTestResult
    ) -> List[str]:
        prompt = build_llm_eval_prompt(test_case, result)
        # self.logger.debug(f"LLM evaluation prompt: {prompt}")
        try:
            import openai

            completion = openai.chat.completions.create(
                model=test_case.llm_model,
                messages=[
                    {"role": "system", "content": "You are a code/project evaluator."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                # max_tokens=512,
            )
            content = completion.choices[0].message.content.strip()
            # Robust JSON extraction
            start = content.find("{")
            end = content.rfind("}") + 1
            content_json = content[start:end]
            parsed = json.loads(content_json)
            llm_result = LLMEvaluationResult(**parsed)
            result.llm_evaluation = llm_result
            if not llm_result.passed:
                return [
                    f"LLM Evaluation failed: {llm_result.reasoning} (score: {llm_result.score})"
                ]
            return []
        except Exception as exc:
            result.llm_evaluation = None
            return [f"LLM evaluation failed: {exc}"]

    def run_test(self, test_case: KatalystTestCase) -> KatalystTestResult:
        """Run a single test case and return its result."""
        start_time = time.time()
        # Use the test case's user_input_config if provided, else default
        self.user_input_config = test_case.user_input_config or self.user_input_config

        result = KatalystTestResult(test_case=test_case, success=False)

        try:
            # --- Take a snapshot of files BEFORE the run ---
            initial_files = set(p.resolve() for p in Path(".").rglob("*"))
            self.logger.debug(
                f"Taking initial file snapshot: {len(initial_files)} files found"
            )

            state = KatalystState(
                task=test_case.task,
                auto_approve=test_case.auto_approve,
                project_root_cwd=str(Path.cwd()),
                user_input_fn=self._simulate_user_input,
            )
            app = build_compiled_graph()
            config = {
                "recursion_limit": int(os.getenv("KATALYST_RECURSION_LIMIT", 250)),
            }

            # --- Run the agent ---
            final_state = app.invoke(state, config)

            # Convert the dictionary back to KatalystState object
            self.logger.debug(f"Graph returned final_state type: {type(final_state)}")
            self.logger.debug(f"Graph returned final_state content: {final_state}")
            if isinstance(final_state, dict):
                self.logger.debug("Converting dict to KatalystState object")
                final_state = KatalystState(**final_state)
                self.logger.debug(
                    f"Converted to KatalystState with response: {final_state.response}"
                )
            else:
                self.logger.debug(
                    f"Final state is already a {type(final_state)} object"
                )

            result.actual_output = final_state.response
            result.execution_time = time.time() - start_time

            # --- Gather only the files created/modified during the test ---
            result.created_files = self._gather_created_files(initial_files)

            errors = self._run_llm_evaluation(test_case, result)
            if errors:
                result.error_messages.extend(errors)
                result.success = False
            else:
                result.success = True
        except Exception as e:
            result.success = False
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
                    "actual_output": r.actual_output,
                    "created_files": list(r.created_files.keys()),
                    "llm_evaluation": r.llm_evaluation.model_dump()
                    if r.llm_evaluation
                    else None,
                }
                for r in results
            ],
        }

        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)

        self.logger.info(f"Test report written to {output_file}")


# ------------------- USAGE EXAMPLE ---------------------
# To use:
# 1. Define test cases as KatalystTestCase objects.
# 2. Call KatalystTestRunner().run_tests(test_cases)
# 3. Call generate_report(results)

# Example test case
if __name__ == "__main__":
    test_cases = [
        KatalystTestCase(
            name="create_math_project",
            task="Create a folder 'mytest' with add.py, multiply.py, divide.py (each with a function), and main.py that calls all three.",
            auto_approve=True,
            llm_eval_instructions="Judge correctness, completeness, and absence of unnecessary files/scripts.",
            llm_rubric=[
                "All required scripts (add.py, multiply.py, divide.py, main.py) are present.",
                "No unnecessary files/scripts are present.",
                "Each script contains a function with the correct name and logic.",
                "main.py imports and calls all three operation scripts.",
            ],
            # user_input_config is not required; defaults to always '1'
        )
    ]
    runner = KatalystTestRunner()  # defaults to always selecting '1'
    results = runner.run_tests(test_cases)
    runner.generate_report(results)


# # Actual pytest test functions
# def test_test_case_creation():
#     """Test that KatalystTestCase can be created with required fields."""
#     test_case = KatalystTestCase(
#         name="test1",
#         task="Test task",
#         expected_output="Expected output",
#         user_inputs=["yes", "no"],
#     )
#     assert test_case.name == "test1"
#     assert test_case.task == "Test task"
#     assert test_case.expected_output == "Expected output"
#     assert test_case.user_inputs == ["yes", "no"]


# def test_test_result_creation():
#     """Test that KatalystTestResult can be created with required fields."""
#     test_case = KatalystTestCase(name="test1", task="Test task")
#     result = KatalystTestResult(
#         test_case=test_case, success=True, actual_output="Test passed"
#     )
#     assert result.test_case == test_case
#     assert result.success is True
#     assert result.actual_output == "Test passed"
#     assert isinstance(result.error_messages, list)
#     assert isinstance(result.created_files, dict)
#     assert isinstance(result.executed_commands, list)


# def test_test_runner_initialization():
#     """Test that KatalystTestRunner can be initialized."""
#     runner = KatalystTestRunner(auto_approve=True)
#     assert runner.auto_approve is True
#     assert runner.logger is not None
