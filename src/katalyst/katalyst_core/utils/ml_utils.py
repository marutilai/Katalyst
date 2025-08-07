"""Utilities for ML-related operations."""
from typing import List


def check_analysis_performed(messages: List, lookback: int = 15) -> bool:
    """
    Check if any analysis tools were used in recent messages.
    
    Args:
        messages: List of conversation messages
        lookback: Number of recent messages to check
        
    Returns:
        True if analysis tools were used (read, ls, analyze_ml_performance)
    """
    recent_messages = messages[-lookback:] if len(messages) > lookback else messages
    analysis_tools = ["analyze_ml_performance", "read", "ls"]
    
    for msg in recent_messages:
        msg_content = str(msg.content)
        if any(tool in msg_content for tool in analysis_tools):
            return True
    
    return False