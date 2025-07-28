"""
Checkpointer Manager - Singleton pattern for sharing checkpointer across agents.

This solves the serialization issue by storing the checkpointer instance
separately from the state, while still allowing all agents to access it.
"""

from typing import Optional
from langgraph.checkpoint.base import BaseCheckpointSaver


class CheckpointerManager:
    """Singleton manager for the global checkpointer."""
    
    _instance: Optional['CheckpointerManager'] = None
    _checkpointer: Optional[BaseCheckpointSaver] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def set_checkpointer(self, checkpointer: BaseCheckpointSaver):
        """Set the global checkpointer."""
        self._checkpointer = checkpointer
    
    def get_checkpointer(self) -> Optional[BaseCheckpointSaver]:
        """Get the global checkpointer."""
        return self._checkpointer


# Global instance
checkpointer_manager = CheckpointerManager()