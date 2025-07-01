"""Test that custom error messages are preserved through error formatting."""
import pytest
from katalyst.katalyst_core.utils.error_handling import (
    ErrorType, 
    format_error_for_llm,
    create_error_message,
    classify_error
)


def test_custom_tool_repetition_message_preserved():
    """Test that custom TOOL_REPETITION messages with escalation markers are preserved."""
    # Test messages with different escalation levels
    custom_messages = [
        "⚠️ CRITICAL: Tool 'read_file' called with IDENTICAL inputs back-to-back! You are STUCK in a repetitive loop. THINK HARDER and CHANGE YOUR STRATEGY COMPLETELY.\n\n💡 HINT: 2 consecutive blocks. Consider if you're trying to re-do something you already accomplished.",
        "🚨 CRITICAL: You've been blocked 5 times in a row! You are COMPLETELY STUCK and need to FUNDAMENTALLY CHANGE YOUR APPROACH.",
        "⚠️ WARNING: 3 consecutive blocked operations! You are stuck in a repetitive pattern. CHANGE YOUR STRATEGY COMPLETELY.",
        "Tool 'list_files' has been called 3 times with identical inputs. STOP repeating the same operation! THINK HARDER about alternative approaches."
    ]
    
    for custom_msg in custom_messages:
        # Create error message
        error_msg = create_error_message(ErrorType.TOOL_REPETITION, custom_msg, "TOOL_RUNNER")
        
        # Classify and format
        error_type, error_details = classify_error(error_msg)
        
        # Check if we should preserve (escalation markers present)
        escalation_markers = ["💡 HINT:", "⚠️ WARNING:", "🚨 CRITICAL:", "THINK HARDER", "consecutive blocks"]
        has_escalation = any(marker in error_details for marker in escalation_markers)
        
        if has_escalation:
            formatted = format_error_for_llm(error_type, error_details, custom_message=error_details)
        else:
            formatted = format_error_for_llm(error_type, error_details)
        
        # Should preserve the custom message
        assert formatted == custom_msg, f"Custom message not preserved: {formatted}"


def test_default_tool_repetition_message_used():
    """Test that default message is used when no escalation markers present."""
    simple_msg = "Tool 'some_tool' was called multiple times"
    
    # Create error message
    error_msg = create_error_message(ErrorType.TOOL_REPETITION, simple_msg, "TOOL_RUNNER")
    
    # Classify and format
    error_type, error_details = classify_error(error_msg)
    formatted = format_error_for_llm(error_type, error_details)
    
    # Should use default formatting
    assert "Repetitive tool call detected:" in formatted
    assert "Please try a different approach" in formatted


def test_custom_tool_error_message_preserved():
    """Test that custom TOOL_ERROR messages with escalation markers are preserved."""
    custom_messages = [
        "⚠️ REDUNDANT OPERATION BLOCKED: Tool 'list_files' was already successfully executed with these inputs. THINK HARDER - you already have this information!\n\n🚨 CRITICAL: You've been blocked 6 times in a row!",
        "REDUNDANT OPERATION BLOCKED: Check your Recent Tool Operations and use the existing information.\n\n💡 HINT: 1 consecutive blocks."
    ]
    
    for custom_msg in custom_messages:
        # Create error message
        error_msg = create_error_message(ErrorType.TOOL_ERROR, custom_msg, "TOOL_RUNNER")
        
        # Classify and format
        error_type, error_details = classify_error(error_msg)
        
        # Check if we should preserve (escalation markers present)
        escalation_markers = ["💡 HINT:", "⚠️ WARNING:", "🚨 CRITICAL:", "THINK HARDER", "consecutive blocks"]
        has_escalation = any(marker in error_details for marker in escalation_markers)
        
        if has_escalation:
            formatted = format_error_for_llm(error_type, error_details, custom_message=error_details)
        else:
            formatted = format_error_for_llm(error_type, error_details)
        
        # Should preserve the custom message
        assert formatted == custom_msg, f"Custom message not preserved: {formatted}"


def test_default_tool_error_message_used():
    """Test that default message is used for regular tool errors."""
    simple_msg = "File not found: /path/to/file.py"
    
    # Create error message
    error_msg = create_error_message(ErrorType.TOOL_ERROR, simple_msg, "TOOL_RUNNER")
    
    # Classify and format
    error_type, error_details = classify_error(error_msg)
    formatted = format_error_for_llm(error_type, error_details)
    
    # Should use default formatting
    assert "Tool execution failed:" in formatted
    assert "Please analyze the error" in formatted


if __name__ == "__main__":
    test_custom_tool_repetition_message_preserved()
    test_default_tool_repetition_message_used()
    test_custom_tool_error_message_preserved()
    test_default_tool_error_message_used()
    print("All tests passed!")