"""
Todo List Persistence

Provides a class-based interface for managing todo lists with automatic
persistence across Katalyst sessions.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.app.config import KATALYST_DIR


class TodoManager:
    """Manages todo list with automatic persistence to disk (Singleton)."""
    
    _instance = None
    
    def __new__(cls, file_path: Optional[Path] = None):
        """Ensure only one instance exists (Singleton pattern)."""
        if cls._instance is None:
            cls._instance = super(TodoManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, file_path: Optional[Path] = None):
        """
        Initialize TodoManager (only runs once due to singleton).
        
        Args:
            file_path: Optional custom path for todo storage. 
                      Defaults to .katalyst/todos.json
        """
        # Only initialize once
        if self._initialized:
            return
            
        self.logger = get_logger()
        self.file_path = file_path or (KATALYST_DIR / "todos.json")
        self._todos: List[Dict[str, Any]] = []
        self._loaded = False
        self._initialized = True
        
    @property
    def todos(self) -> List[Dict[str, Any]]:
        """Get all todos, loading from disk if needed."""
        if not self._loaded:
            self.load()
        return self._todos
    
    @property
    def pending(self) -> List[Dict[str, Any]]:
        """Get pending todos."""
        return [t for t in self.todos if t.get("status") == "pending"]
    
    @property
    def in_progress(self) -> List[Dict[str, Any]]:
        """Get in-progress todos."""
        return [t for t in self.todos if t.get("status") == "in_progress"]
    
    @property
    def completed(self) -> List[Dict[str, Any]]:
        """Get completed todos."""
        return [t for t in self.todos if t.get("status") == "completed"]
    
    def load(self) -> bool:
        """
        Load todos from disk.
        
        Returns:
            True if loaded successfully
        """
        try:
            if not self.file_path.exists():
                self.logger.debug(f"[TODO_MANAGER] No existing todo file at {self.file_path}")
                self._todos = []
                self._loaded = True
                return True
            
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            
            # Validate structure
            if not isinstance(data, dict) or "todos" not in data:
                self.logger.warning("[TODO_MANAGER] Invalid todo file format")
                self._todos = []
                self._loaded = True
                return False
            
            self._todos = data["todos"]
            self._loaded = True
            
            # Log summary
            self.logger.info(f"[TODO_MANAGER] Loaded {len(self._todos)} todos from previous session")
            if self.pending or self.in_progress:
                self.logger.info(
                    f"[TODO_MANAGER] Status: {len(self.pending)} pending, "
                    f"{len(self.in_progress)} in progress, {len(self.completed)} completed"
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"[TODO_MANAGER] Failed to load todos: {e}")
            self._todos = []
            self._loaded = True
            return False
    
    def save(self) -> bool:
        """
        Save todos to disk.
        
        Returns:
            True if saved successfully
        """
        try:
            # Ensure directory exists
            self.file_path.parent.mkdir(exist_ok=True)
            
            # Save todos as JSON
            with open(self.file_path, 'w') as f:
                json.dump({
                    "version": "1.0",
                    "todos": self._todos
                }, f, indent=2)
            
            self.logger.debug(f"[TODO_MANAGER] Saved {len(self._todos)} todos to {self.file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"[TODO_MANAGER] Failed to save todos: {e}")
            return False
    
    def clear(self) -> bool:
        """
        Clear all todos and remove storage file.
        
        Returns:
            True if cleared successfully
        """
        try:
            self._todos = []
            if self.file_path.exists():
                self.file_path.unlink()
            self.logger.debug("[TODO_MANAGER] Cleared todo storage")
            return True
            
        except Exception as e:
            self.logger.error(f"[TODO_MANAGER] Failed to clear todos: {e}")
            return False
    
    def add(self, content: str, status: str = "pending", priority: str = "medium", 
            todo_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Add a new todo.
        
        Args:
            content: Todo description
            status: Todo status (pending, in_progress, completed)
            priority: Todo priority (low, medium, high)
            todo_id: Optional ID, will generate if not provided
            
        Returns:
            The created todo
        """
        if not todo_id:
            # Generate ID based on current max ID
            max_id = max([int(t["id"]) for t in self.todos if t.get("id", "").isdigit()] + [0])
            todo_id = str(max_id + 1)
        
        todo = {
            "id": todo_id,
            "content": content,
            "status": status,
            "priority": priority
        }
        
        self._todos.append(todo)
        self.save()
        return todo
    
    def update(self, todo_id: str, **updates) -> Optional[Dict[str, Any]]:
        """
        Update a todo by ID.
        
        Args:
            todo_id: ID of todo to update
            **updates: Fields to update (content, status, priority)
            
        Returns:
            Updated todo if found, None otherwise
        """
        for todo in self._todos:
            if todo.get("id") == todo_id:
                todo.update(updates)
                self.save()
                return todo
        return None
    
    def get_by_id(self, todo_id: str) -> Optional[Dict[str, Any]]:
        """Get a todo by ID."""
        for todo in self._todos:
            if todo.get("id") == todo_id:
                return todo
        return None
    
    def set_todos(self, todos: List[Dict[str, Any]]) -> bool:
        """
        Replace all todos with a new list.
        
        Args:
            todos: New todo list
            
        Returns:
            True if saved successfully
        """
        self._todos = todos
        self._loaded = True
        return self.save()
    
    def get_summary(self) -> str:
        """
        Get a human-readable summary of todos.
        
        Returns:
            Formatted summary string
        """
        if not self.todos:
            return "No todos found"
        
        summary_lines = []
        
        if self.in_progress:
            summary_lines.append("In Progress:")
            for t in self.in_progress:
                summary_lines.append(f"  - {t['content']}")
        
        if self.pending:
            summary_lines.append("Pending:")
            for t in self.pending[:5]:  # Show first 5
                summary_lines.append(f"  - {t['content']}")
            if len(self.pending) > 5:
                summary_lines.append(f"  ... and {len(self.pending) - 5} more")
        
        if self.completed:
            summary_lines.append(f"Completed: {len(self.completed)} tasks")
        
        return "\n".join(summary_lines) if summary_lines else "All tasks completed!"
    
    @classmethod
    def get_instance(cls) -> 'TodoManager':
        """Get the singleton instance of TodoManager."""
        if cls._instance is None:
            cls._instance = TodoManager()
        return cls._instance


# Singleton instance for backward compatibility
_todo_manager = TodoManager.get_instance()


# Backward compatibility functions
def save_todos(todos: List[Dict[str, Any]]) -> bool:
    """Legacy function - use TodoManager instead."""
    return _todo_manager.set_todos(todos)


def load_todos() -> Optional[List[Dict[str, Any]]]:
    """Legacy function - use TodoManager instead."""
    if _todo_manager.load():
        return _todo_manager.todos
    return None


def clear_todos() -> bool:
    """Legacy function - use TodoManager instead."""
    return _todo_manager.clear()


def get_todo_summary() -> str:
    """Legacy function - use TodoManager instead."""
    return _todo_manager.get_summary()