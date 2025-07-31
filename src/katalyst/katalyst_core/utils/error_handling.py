from enum import Enum


class ErrorType(Enum):
    """
    Error types used across the Katalyst agent system.
    
    These are used to create structured error messages that the LLM can understand.
    """
    TOOL_ERROR = "TOOL_ERROR"  # Tool execution failures
    PARSING_ERROR = "PARSING_ERROR"  # Invalid state or response format
    LLM_ERROR = "LLM_ERROR"  # Critical LLM-related failures
    REPLAN_REQUESTED = "REPLAN_REQUESTED"  # User requested replanning
    SANDBOX_VIOLATION = "SANDBOX_VIOLATION"  # Attempted access outside project directory


def create_error_message(
    error_type: ErrorType, message: str, component: str = ""
) -> str:
    """
    Creates a standardized error message with proper tagging.

    Format: [COMPONENT] [ERROR_TYPE] message

    Args:
        error_type: Type of error from ErrorType enum
        message: Detailed error message
        component: Component name (e.g., "PLANNER", "AGENT_REACT")

    Returns:
        Formatted error message string
    """
    component_tag = f"[{component}] " if component else ""
    return f"{component_tag}[{error_type.value}] {message}"
