"""
Operation Context Tracking

Provides multi-level context tracking for agent operations to prevent
duplication and improve awareness of recent actions.
"""

import os
from typing import List, Dict, Tuple, Optional, Any
from collections import deque
from datetime import datetime
from pydantic import BaseModel, Field


class FileOperation(BaseModel):
    """Represents a file operation performed by the agent."""
    file_path: str = Field(..., description="Path to the file")
    operation: str = Field(..., description="Type of operation (created, modified, read)")
    timestamp: datetime = Field(default_factory=datetime.now)
    details: Optional[str] = Field(None, description="Additional operation details")


class ToolOperation(BaseModel):
    """Represents a tool operation performed by the agent."""
    tool_name: str = Field(..., description="Name of the tool")
    tool_input: Dict = Field(default_factory=dict, description="Tool input parameters")
    success: bool = Field(..., description="Whether the operation succeeded")
    timestamp: datetime = Field(default_factory=datetime.now)
    summary: Optional[str] = Field(None, description="Brief summary of the result")


class OperationContext:
    """
    Tracks multi-level context of agent operations with configurable history.
    
    Maintains three levels of context:
    1. File operations (creates, modifies, reads)
    2. Tool operations (all tool calls)
    3. Task context (handled separately)
    """
    
    def __init__(
        self,
        file_history_limit: int = 10,
        operations_history_limit: int = 10
    ):
        """
        Initialize operation context tracker.
        
        Args:
            file_history_limit: Maximum number of file operations to track
            operations_history_limit: Maximum number of tool operations to track
        """
        self.file_operations: deque[FileOperation] = deque(maxlen=file_history_limit)
        self.tool_operations: deque[ToolOperation] = deque(maxlen=operations_history_limit)
        self._file_history_limit = file_history_limit
        self._operations_history_limit = operations_history_limit
    
    def add_file_operation(
        self,
        file_path: str,
        operation: str,
        details: Optional[str] = None
    ) -> None:
        """
        Track a file operation.
        
        Args:
            file_path: Path to the file
            operation: Type of operation (created, modified, read)
            details: Additional operation details
        """
        # Normalize the file path
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)
        
        self.file_operations.append(FileOperation(
            file_path=file_path,
            operation=operation,
            details=details
        ))
    
    def add_tool_operation(
        self,
        tool_name: str,
        tool_input: Dict,
        success: bool,
        summary: Optional[str] = None
    ) -> None:
        """
        Track a tool operation.
        
        Args:
            tool_name: Name of the tool
            tool_input: Tool input parameters
            success: Whether the operation succeeded
            summary: Brief summary of the result
        """
        self.tool_operations.append(ToolOperation(
            tool_name=tool_name,
            tool_input=tool_input,
            success=success,
            summary=summary
        ))
    
    def get_recent_files(self, operation_type: Optional[str] = None) -> List[str]:
        """
        Get list of recently operated files.
        
        Args:
            operation_type: Filter by operation type (created, modified, read)
            
        Returns:
            List of file paths
        """
        if operation_type:
            return [
                op.file_path
                for op in self.file_operations
                if op.operation == operation_type
            ]
        return [op.file_path for op in self.file_operations]
    
    def has_recent_operation(self, tool_name: str, tool_input: Dict[str, Any]) -> bool:
        """
        Check if a specific tool operation was recently performed with the same inputs.
        
        Args:
            tool_name: Name of the tool
            tool_input: Tool input parameters to check
            
        Returns:
            True if the operation was recently performed, False otherwise
        """
        # For read operations, check if the file was recently read
        if tool_name == "read_file" and "path" in tool_input:
            target_path = tool_input["path"]
            # Normalize the path for comparison
            if not os.path.isabs(target_path):
                target_path = os.path.abspath(target_path)
            
            # Check in tool operations for successful reads
            for op in self.tool_operations:
                if (op.tool_name == "read_file" and 
                    op.success and 
                    "path" in op.tool_input):
                    op_path = op.tool_input["path"]
                    if not os.path.isabs(op_path):
                        op_path = os.path.abspath(op_path)
                    if op_path == target_path:
                        return True
        
        # For list_files, check if same directory was recently listed
        elif tool_name == "list_files" and "path" in tool_input:
            target_path = tool_input["path"]
            if not os.path.isabs(target_path):
                target_path = os.path.abspath(target_path)
            
            for op in self.tool_operations:
                if (op.tool_name == "list_files" and 
                    op.success and 
                    "path" in op.tool_input):
                    op_path = op.tool_input["path"]
                    if not os.path.isabs(op_path):
                        op_path = os.path.abspath(op_path)
                    if op_path == target_path:
                        return True
        
        # For search operations, check if same pattern was recently searched
        elif tool_name in ["search_in_file", "search_in_directory"]:
            pattern = tool_input.get("pattern", "")
            path = tool_input.get("path", "")
            
            for op in self.tool_operations:
                if (op.tool_name == tool_name and 
                    op.success and 
                    op.tool_input.get("pattern") == pattern and
                    op.tool_input.get("path") == path):
                    return True
        
        return False
    
    def was_file_created(self, file_path: str) -> bool:
        """Check if a file was recently created."""
        # Normalize the path for comparison
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)
        
        for op in self.file_operations:
            if op.file_path == file_path and op.operation == "created":
                return True
        return False
    
    def get_context_for_agent(self) -> str:
        """
        Format operation context for inclusion in agent prompt.
        
        Returns:
            Formatted context string
        """
        lines = []
        
        # File operations section
        if self.file_operations:
            lines.append("=== Recent File Operations ===")
            # Show most recent first
            for op in reversed(self.file_operations):
                # Make path relative for display
                display_path = op.file_path
                if os.path.isabs(display_path):
                    try:
                        display_path = os.path.relpath(display_path)
                    except ValueError:
                        pass  # Keep absolute if can't make relative
                
                line = f"- {op.operation}: {display_path}"
                if op.details:
                    line += f" ({op.details})"
                lines.append(line)
            lines.append("")
        
        # Tool operations section
        if self.tool_operations:
            lines.append("=== Recent Tool Operations ===")
            # Show most recent first
            for op in reversed(self.tool_operations):
                status = "✓" if op.success else "✗"
                line = f"{status} {op.tool_name}"
                
                # Add key parameters for context
                if op.tool_name == "write_to_file" and "path" in op.tool_input:
                    line += f": {op.tool_input['path']}"
                elif op.tool_name == "read_file" and "path" in op.tool_input:
                    line += f": {op.tool_input['path']}"
                elif op.tool_name == "create_subtask" and "task_description" in op.tool_input:
                    task_desc = op.tool_input['task_description']
                    # Truncate long descriptions
                    if len(task_desc) > 50:
                        task_desc = task_desc[:47] + "..."
                    line += f": {task_desc}"
                
                if op.summary:
                    line += f" - {op.summary}"
                
                lines.append(line)
        
        return "\n".join(lines) if lines else ""
    
    def clear(self) -> None:
        """Clear all tracked operations."""
        self.file_operations.clear()
        self.tool_operations.clear()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "file_operations": [op.model_dump() for op in self.file_operations],
            "tool_operations": [op.model_dump() for op in self.tool_operations],
            "file_history_limit": self._file_history_limit,
            "operations_history_limit": self._operations_history_limit
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "OperationContext":
        """Create from dictionary."""
        context = cls(
            file_history_limit=data.get("file_history_limit", 10),
            operations_history_limit=data.get("operations_history_limit", 10)
        )
        
        # Restore file operations
        for op_data in data.get("file_operations", []):
            context.file_operations.append(FileOperation(**op_data))
        
        # Restore tool operations
        for op_data in data.get("tool_operations", []):
            context.tool_operations.append(ToolOperation(**op_data))
        
        return context