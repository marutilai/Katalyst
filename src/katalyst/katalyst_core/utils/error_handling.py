from enum import Enum
from typing import Optional, Tuple


class ErrorType(Enum):
    """
    Error types used across the Katalyst agent system.

    Error Handling Strategies:
    - TOOL_ERROR: Tool execution failures. Propagates as observations in action trace.
                  Agent can retry with different tools/approaches.
    - PARSING_ERROR: Invalid state or response format. Triggers retries or state resets.
                    Minimal state impact, often just resets specific variables.
    - LLM_ERROR: Critical LLM-related failures. Often leads to task termination.
                 Sets both error_message and response.
    - REPLAN_REQUESTED: Special type for agent-initiated replanning.
                       Triggers high-level replanning flow.
    - GRAPH_RECURSION: Indicates a recursion error in the graph execution.
                      Triggers replanning to handle the error gracefully.
    - CONTENT_OMISSION: Content validation failure in write operations.
                       Indicates LLM truncated or omitted content when line count mismatch detected.
    - TOOL_REPETITION: Repetitive tool calls detected. Prevents infinite loops.
    - UNKNOWN: Fallback for unclassified errors.
    """

    TOOL_ERROR = "TOOL_ERROR"
    PARSING_ERROR = "PARSING_ERROR"
    LLM_ERROR = "LLM_ERROR"
    REPLAN_REQUESTED = "REPLAN_REQUESTED"
    GRAPH_RECURSION = "GRAPH_RECURSION"
    CONTENT_OMISSION = "CONTENT_OMISSION"
    TOOL_REPETITION = "TOOL_REPETITION"
    UNKNOWN = "UNKNOWN"


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


def classify_error(error_message: str) -> Tuple[ErrorType, str]:
    """
    Classifies an error message into its type and extracts details.

    Args:
        error_message: The error message to classify

    Returns:
        Tuple of (ErrorType, error details)
    """
    error_types = {
        "[TOOL_ERROR]": ErrorType.TOOL_ERROR,
        "[PARSING_ERROR]": ErrorType.PARSING_ERROR,
        "[LLM_ERROR]": ErrorType.LLM_ERROR,
        "[REPLAN_REQUESTED]": ErrorType.REPLAN_REQUESTED,
        "[GRAPH_RECURSION]": ErrorType.GRAPH_RECURSION,
        "[CONTENT_OMISSION]": ErrorType.CONTENT_OMISSION,
        "[TOOL_REPETITION]": ErrorType.TOOL_REPETITION,
    }

    for tag, error_type in error_types.items():
        if tag in error_message:
            # Remove the tag and any component prefix
            cleaned_message = error_message.split(tag)[-1].strip()
            # Remove component tag if present
            if cleaned_message.startswith("[") and "]" in cleaned_message:
                cleaned_message = cleaned_message.split("]", 1)[-1].strip()
            return error_type, cleaned_message

    return ErrorType.UNKNOWN, error_message


def format_error_for_llm(error_type: ErrorType, error_details: str, custom_message: Optional[str] = None) -> str:
    """
    Formats error information for LLM understanding and action.

    Args:
        error_type: Type of error from ErrorType enum
        error_details: Detailed error message
        custom_message: Optional pre-formatted message that takes priority

    Returns:
        Formatted error message for LLM consumption
    """
    # If custom message is provided, use it directly
    if custom_message is not None:
        return custom_message
    if error_type == ErrorType.TOOL_ERROR:
        return (
            f"Tool execution failed: {error_details}\n"
            "Please analyze the error and try a different approach or tool."
        )
    elif error_type == ErrorType.PARSING_ERROR:
        return (
            f"Failed to parse LLM response: {error_details}\n"
            "Please ensure your response follows the required format."
        )
    elif error_type == ErrorType.LLM_ERROR:
        return (
            f"LLM encountered an error: {error_details}\n"
            "Please try again with a different approach."
        )
    elif error_type == ErrorType.REPLAN_REQUESTED:
        return (
            f"Replanning requested: {error_details}\n"
            "The current approach isn't working. Please request replanning."
        )
    elif error_type == ErrorType.GRAPH_RECURSION:
        return (
            f"Graph recursion detected: {error_details}\n"
            "The current execution path has entered a loop. Please request replanning to try a different approach."
        )
    elif error_type == ErrorType.CONTENT_OMISSION:
        # Extract line count info to provide specific guidance
        import re
        match = re.search(r"predicted (\d+) lines.*provided (\d+) lines", error_details)
        if match:
            predicted = int(match.group(1))
            actual = int(match.group(2))
            difference = predicted - actual
            
            return (
                f"Content omission detected: {error_details}\n\n"
                f"You were off by {abs(difference)} lines. Count more carefully:\n"
                "• Count EVERY line including empty ones\n"
                "• Each \\n creates a new line (even at EOF)\n"
                "• Double-check: did you skip empty lines or truncate content?\n"
                "Please provide the COMPLETE content with accurate line count."
            )
        else:
            return (
                f"Content omission detected: {error_details}\n"
                "Count ALL lines including empty ones. Each \\n = new line.\n"
                "Please provide the COMPLETE content with accurate line count."
            )
    elif error_type == ErrorType.TOOL_REPETITION:
        return (
            f"Repetitive tool call detected: {error_details}\n"
            "You are repeatedly calling the same tool with identical inputs. "
            "Please try a different approach, use a different tool, or reconsider your strategy."
        )
    return f"Unknown error occurred: {error_details}"
