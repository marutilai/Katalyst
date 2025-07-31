"""Custom exceptions for Katalyst."""

from typing import List, Optional


class UserInputRequiredException(Exception):
    """
    Raised when a tool needs user input during execution.
    
    This exception is used to interrupt agent execution and return control
    to the main REPL for handling user interaction.
    """
    
    def __init__(
        self, 
        question: str, 
        suggested_responses: List[str],
        tool_name: str = "request_user_input"
    ):
        self.question = question
        self.suggested_responses = suggested_responses
        self.tool_name = tool_name
        super().__init__(f"User input required: {question}")


class SandboxViolationError(Exception):
    """
    Raised when a tool attempts to access a path outside the project directory.
    
    This exception enforces the security sandbox that restricts all file
    operations to within the project root directory.
    """
    
    def __init__(self, attempted_path: str, project_root: str):
        self.attempted_path = attempted_path
        self.project_root = project_root
        super().__init__(
            f"Access denied: Path '{attempted_path}' is outside the project directory '{project_root}'. "
            f"All file operations must remain within the project directory for security."
        )