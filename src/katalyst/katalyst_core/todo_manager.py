"""
Todo Manager for Katalyst - Manages todo lists and persists them to markdown files.
"""
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
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
        
        # Load existing todos if file exists
        self.load_from_file()
        
    def create_list(self, items: List[str], task_description: str = ""):
        """Create a new todo list."""
        self.todos = items.copy()
        self.completed = []
        self.current_task = task_description
        self.start_time = datetime.now()
        # Reset _last_complete_time to ensure correct duration calculations
        if hasattr(self, '_last_complete_time'):
            del self._last_complete_time
        self.logger.info(f"[TodoManager] 📋 Created todo list with {len(items)} items (0/{len(items)} completed)")
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
            # Get progress info for logging
            progress = self.get_progress_info()
            self.logger.info(f"[TodoManager] ✓ Completed ({progress['completed']}/{progress['total']}): {item}")
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
    
    def get_progress_info(self):
        """Get current progress information."""
        completed_count = len(self.completed)
        total_count = completed_count + len(self.todos)
        current_task = self.todos[0] if self.todos else None
        
        return {
            "completed": completed_count,
            "total": total_count,
            "current_task": current_task,
            "percentage": int((completed_count / total_count * 100)) if total_count > 0 else 0
        }
        
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
    
    def load_from_file(self):
        """Load todo list from markdown file if it exists."""
        if not os.path.exists(self.file_path):
            self.logger.debug(f"[TodoManager] No existing todo file found at {self.file_path}")
            return
            
        try:
            with open(self.file_path, 'r') as f:
                content = f.read()
                
            # Parse the markdown content
            lines = content.split('\n')
            parsing_todos = False
            
            for line in lines:
                line = line.strip()
                
                # Extract task description
                if line.startswith("**Task**:"):
                    self.current_task = line.split(":", 1)[1].strip()
                    if self.current_task == "General Development":
                        self.current_task = None
                        
                # Look for the todo section
                if line.startswith("## Current ToDos"):
                    parsing_todos = True
                    continue
                    
                # Parse todo items
                if parsing_todos and line.startswith("-"):
                    if line.startswith("- [x]"):
                        # Completed task
                        task_match = line[6:].strip()
                        # Remove duration info
                        if " *(" in task_match:
                            task_text = task_match.split(" *(")[0]
                            duration_str = task_match.split(" *(")[1].rstrip(")*")
                            duration_mins = int(duration_str.split()[0])
                        else:
                            task_text = task_match
                            duration_mins = 0
                            
                        self.completed.append({
                            "task": task_text,
                            "duration_mins": duration_mins,
                            "completed_at": datetime.now()  # Approximate
                        })
                    elif line.startswith("- [→]") or line.startswith("- [ ]"):
                        # Pending task
                        task_text = line[6:].strip()
                        self.todos.append(task_text)
                        
            self.logger.info(f"[TodoManager] Loaded {len(self.todos)} pending and {len(self.completed)} completed todos from disk")
            
        except Exception as e:
            self.logger.error(f"[TodoManager] Failed to load todo list: {e}")
            # Reset to empty state on error
            self.todos = []
            self.completed = []
            self.current_task = None


