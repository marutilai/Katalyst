"""
Todo Manager for Katalyst - Manages todo lists and persists them to markdown files.
"""
import os
import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable
from functools import wraps
from katalyst.katalyst_core.utils.logger import get_logger


class TodoManager:
    """Singleton manager for todo lists with file persistence."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, file_path: str = ".katalyst/todo_list.md"):
        if self._initialized:
            return
            
        self.file_path = file_path
        self.todos: List[str] = []
        self.completed: List[Dict[str, Any]] = []
        self.current_task: Optional[str] = None
        self.start_time = datetime.now()
        self.logger = get_logger()
        self._initialized = True
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        
    def create_list(self, items: List[str], task_description: str = ""):
        """Create a new todo list."""
        self.todos = items.copy()
        self.completed = []
        self.current_task = task_description
        self.start_time = datetime.now()
        self.logger.info(f"[TodoManager] Created todo list with {len(items)} items")
        self.save_to_file()
        
    def add_item(self, item: str):
        """Add a new todo item."""
        self.todos.append(item)
        self.logger.debug(f"[TodoManager] Added item: {item}")
        self.save_to_file()
        
    def remove_item(self, index: int):
        """Remove a todo item by index (0-based)."""
        if 0 <= index < len(self.todos):
            removed = self.todos.pop(index)
            self.logger.debug(f"[TodoManager] Removed item: {removed}")
            self.save_to_file()
            
    def complete_item(self, index: int):
        """Mark a todo item as complete (0-based index)."""
        if 0 <= index < len(self.todos):
            item = self.todos.pop(index)
            self.completed.append({
                "task": item,
                "completed_at": datetime.now().strftime("%H:%M"),
                "duration_mins": self._calculate_duration()
            })
            self.logger.info(f"[TodoManager] Completed: {item}")
            self.save_to_file()
            
    def reorder_item(self, old_index: int, new_index: int):
        """Move a todo item to a new position (0-based indices)."""
        if 0 <= old_index < len(self.todos) and 0 <= new_index <= len(self.todos):
            item = self.todos.pop(old_index)
            self.todos.insert(new_index, item)
            self.logger.debug(f"[TodoManager] Reordered item: {item}")
            self.save_to_file()
            
    def complete_all_remaining(self, reason: str = "Task completed"):
        """Mark all remaining todos as completed."""
        while self.todos:
            self.complete_item(0)
        self.logger.info(f"[TodoManager] Completed all remaining items: {reason}")
        self.save_to_file()
        
    def get_current_list(self) -> List[str]:
        """Get the current todo list."""
        return self.todos.copy()
        
    def _calculate_duration(self) -> int:
        """Calculate duration in minutes since start."""
        if hasattr(self, '_last_complete_time'):
            duration = (datetime.now() - self._last_complete_time).seconds // 60
        else:
            duration = (datetime.now() - self.start_time).seconds // 60
        self._last_complete_time = datetime.now()
        return max(1, duration)  # At least 1 minute
        
    def save_to_file(self):
        """Save the current todo list to a markdown file."""
        try:
            completed_count = len(self.completed)
            total_count = completed_count + len(self.todos)
            
            content = f"""# 📋 Katalyst Todo List

**Task**: {self.current_task or "General Development"}  
**Started**: {self.start_time.strftime("%Y-%m-%d %H:%M:%S")}

## Current ToDos [Status: {completed_count}/{total_count}]
"""
            
            # All tasks in one list
            # First, completed tasks
            for item in self.completed:
                content += f"- [x] {item['task']} *({item['duration_mins']} min)*\n"
            
            # Then, pending tasks
            for i, todo in enumerate(self.todos):
                if i == 0:
                    content += f"- [→] {todo}\n"
                else:
                    content += f"- [ ] {todo}\n"
            
            content += "\n"
            
            # Write to file
            with open(self.file_path, 'w') as f:
                f.write(content)
                
            self.logger.debug(f"[TodoManager] Saved todo list to {self.file_path}")
            
        except Exception as e:
            self.logger.error(f"[TodoManager] Failed to save todo list: {e}")


def todo_aware(action: str = "update"):
    """
    Decorator for tools that interact with the todo list.
    
    Actions:
    - create: For create_todo_list tool
    - update: For update_todo_list tool
    - complete_all: For attempt_completion tool
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Execute the original function
            result = func(*args, **kwargs)
            
            # Get or create TodoManager instance
            manager = TodoManager()
            logger = get_logger()
            
            try:
                if action == "create":
                    # Parse result for create_todo_list
                    if isinstance(result, str):
                        data = json.loads(result)
                        if data.get("success") and data.get("todo_list"):
                            task_desc = kwargs.get("task_description", "Development Task")
                            manager.create_list(data["todo_list"], task_desc)
                            logger.info(f"[todo_aware] Created todo list with {len(data['todo_list'])} items")
                            
                elif action == "update":
                    # Handle update_todo_list actions
                    update_action = kwargs.get("action")
                    
                    if update_action == "add":
                        task = kwargs.get("task_description")
                        if task:
                            manager.add_item(task)
                            
                    elif update_action == "remove":
                        idx = kwargs.get("task_index")
                        if idx is not None:
                            manager.remove_item(idx - 1)  # Convert to 0-based
                            
                    elif update_action == "complete":
                        idx = kwargs.get("task_index")
                        if idx is not None:
                            manager.complete_item(idx - 1)  # Convert to 0-based
                            
                    elif update_action == "reorder":
                        old_idx = kwargs.get("task_index")
                        new_idx = kwargs.get("new_position")
                        if old_idx is not None and new_idx is not None:
                            manager.reorder_item(old_idx - 1, new_idx - 1)  # Convert to 0-based
                            
                    elif update_action == "show":
                        # Update the result to include current list
                        if isinstance(result, str):
                            data = json.loads(result)
                            data["updated_list"] = manager.get_current_list()
                            result = json.dumps(data, indent=2)
                            
                elif action == "complete_all":
                    # For attempt_completion
                    manager.complete_all_remaining("Task marked as completed")
                    logger.info("[todo_aware] Marked all remaining todos as complete")
                    
            except Exception as e:
                logger.error(f"[todo_aware] Error updating todo list: {e}")
                
            return result
            
        return wrapper
    return decorator