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