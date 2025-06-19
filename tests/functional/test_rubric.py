from pydantic import BaseModel, Field
from typing import List, Optional


class RubricItemResult(BaseModel):
    """
    Stores the evaluation result for a single, specific criterion from the rubric.
    This represents the LLM's "answer" to one of the rubric questions.
    """

    criterion: str = Field(..., description="The rubric criterion that was evaluated.")
    passed: bool = Field(..., description="Whether this specific criterion was met.")
    feedback: str = Field(
        ..., description="Specific reasoning for this criterion's pass/fail status."
    )


class KatalystRubric(BaseModel):
    """A standardized set of evaluation criteria for test cases."""

    # --- Correctness & Completeness ---
    all_required_files_created: bool = Field(
        False, description="Checks if all explicitly requested files were created."
    )
    code_is_logically_correct: bool = Field(
        False, description="Checks if the generated code functions as intended."
    )
    code_is_complete: bool = Field(
        False, description="Checks if the code is complete and not stubbed out."
    )

    # --- Cleanliness & Best Practices ---
    no_unnecessary_files_created: bool = Field(
        False, description="Checks that no extra, unexpected files were created."
    )
    has_sufficient_comments_and_docstrings: bool = Field(
        False, description="Checks for adequate documentation within the code."
    )

    # --- Testing & Validation ---
    tests_were_created_or_updated: bool = Field(
        False,
        description="Checks if unit/functional tests were part of the deliverable.",
    )
    validation_command_was_run: bool = Field(
        False,
        description="Checks if the agent ran a command to verify its own work (e.g., 'python main.py' or 'pytest').",
    )

    # --- Custom, Ad-hoc Checks ---
    custom_checks: Optional[List[str]] = Field(
        None, description="A list of any other specific, one-off criteria to check."
    )

    def to_list(self) -> List[str]:
        """Converts the enabled rubric fields into a list of strings for the LLM prompt."""
        rubric_list = []
        if self.all_required_files_created:
            rubric_list.append("All required files were created as specified.")
        if self.code_is_logically_correct:
            rubric_list.append(
                "The generated code is logically correct and fulfills the task requirements."
            )
        if self.code_is_complete:
            rubric_list.append(
                "The generated code is complete and free of placeholders or stubs."
            )
        if self.no_unnecessary_files_created:
            rubric_list.append("No unnecessary or unexpected files were created.")
        if self.has_sufficient_comments_and_docstrings:
            rubric_list.append(
                "The code includes appropriate comments and/or docstrings for clarity."
            )
        if self.tests_were_created_or_updated:
            rubric_list.append(
                "The agent correctly created or updated test files for the new code."
            )
        if self.validation_command_was_run:
            rubric_list.append(
                "The agent ran a command to validate its work (e.g., running the script or tests)."
            )
        if self.custom_checks:
            rubric_list.extend(self.custom_checks)

        return rubric_list
