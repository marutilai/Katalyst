"""
Tool repetition detection to prevent infinite loops in agent execution.
"""
from collections import deque
import hashlib
import json
from typing import Dict, Any, Tuple
from pydantic import BaseModel, Field, ConfigDict


class ToolRepetitionDetector(BaseModel):
    """
    Detects repetitive tool calls to prevent infinite loops.
    
    This detector tracks recent tool calls and identifies when the agent
    is stuck in a loop by calling the same tool with identical inputs
    multiple times.
    """
    
    # Store recent calls as (tool_name, input_hash) tuples
    recent_calls: deque[Tuple[str, str]] = Field(
        default_factory=lambda: deque(maxlen=5),
        description="Recent tool calls stored as (tool_name, input_hash) tuples"
    )
    repetition_threshold: int = Field(
        default=3,
        description="Number of identical calls before flagging as repetition"
    )
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def _hash_input(self, tool_input: Dict[str, Any]) -> str:
        """
        Create a hash of tool input for comparison.
        
        Args:
            tool_input: Dictionary of tool input parameters
            
        Returns:
            MD5 hash of the normalized input
        """
        # Normalize the input by sorting keys and converting to JSON
        # This ensures consistent hashing regardless of key order
        try:
            normalized = json.dumps(tool_input, sort_keys=True)
        except (TypeError, ValueError):
            # Fallback for non-JSON-serializable inputs
            normalized = str(tool_input)
        
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def check(self, tool_name: str, tool_input: Dict[str, Any]) -> bool:
        """
        Check if this tool call is a repetition.
        
        Args:
            tool_name: Name of the tool being called
            tool_input: Input parameters for the tool
            
        Returns:
            True if OK to proceed (not a repetition), False if repetition detected
        """
        input_hash = self._hash_input(tool_input)
        current_call = (tool_name, input_hash)
        
        # Count how many times this exact call appears in recent history
        repetition_count = sum(1 for call in self.recent_calls if call == current_call)
        
        # Add to history
        self.recent_calls.append(current_call)
        
        # Return False if we've exceeded the threshold
        # Note: We count before adding, so if count >= threshold, this is the (threshold+1)th call
        return repetition_count < self.repetition_threshold
    
    def reset(self):
        """Reset the detector (e.g., when starting a new task)."""
        self.recent_calls.clear()
    
    def get_repetition_count(self, tool_name: str, tool_input: Dict[str, Any]) -> int:
        """
        Get the number of times this exact call has been made recently.
        
        Args:
            tool_name: Name of the tool
            tool_input: Input parameters for the tool
            
        Returns:
            Number of times this call appears in recent history
        """
        input_hash = self._hash_input(tool_input)
        target_call = (tool_name, input_hash)
        return sum(1 for call in self.recent_calls if call == target_call)
    
    def is_consecutive_duplicate(self, tool_name: str, tool_input: Dict[str, Any]) -> bool:
        """
        Check if this is an immediate back-to-back duplicate call.
        
        Args:
            tool_name: Name of the tool
            tool_input: Input parameters for the tool
            
        Returns:
            True if this is the exact same call as the previous one
        """
        if not self.recent_calls:
            return False
        
        input_hash = self._hash_input(tool_input)
        current_call = (tool_name, input_hash)
        return self.recent_calls[-1] == current_call