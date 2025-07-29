"""
Unified Task Management System

Combines task tracking for agent execution with persistent task storage.
Provides a singleton interface for managing tasks across Katalyst sessions.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.app.config import KATALYST_DIR


class TaskManager:
    """Manages tasks with automatic persistence to disk (Singleton)."""
    
    _instance = None
    
    def __new__(cls, file_path: Optional[Path] = None):
        """Ensure only one instance exists (Singleton pattern)."""
        if cls._instance is None:
            cls._instance = super(TaskManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, file_path: Optional[Path] = None):
        """
        Initialize TaskManager (only runs once due to singleton).
        
        Args:
            file_path: Optional custom path for task storage. 
                      Defaults to .katalyst/tasks.json
        """
        # Only initialize once
        if self._initialized:
            return
            
        self.logger = get_logger()
        self.file_path = file_path or (KATALYST_DIR / "tasks.json")
        self._tasks: List[Dict[str, Any]] = []
        self._loaded = False
        self._initialized = True
        
    @property
    def tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks, loading from disk if needed."""
        if not self._loaded:
            self.load()
        return self._tasks
    
    @property
    def pending(self) -> List[Dict[str, Any]]:
        """Get pending tasks."""
        return [t for t in self.tasks if t.get("status") == "pending"]
    
    @property
    def in_progress(self) -> List[Dict[str, Any]]:
        """Get in-progress tasks."""
        return [t for t in self.tasks if t.get("status") == "in_progress"]
    
    @property
    def completed(self) -> List[Dict[str, Any]]:
        """Get completed tasks."""
        return [t for t in self.tasks if t.get("status") == "completed"]
    
    def load(self) -> bool:
        """
        Load tasks from disk.
        
        Returns:
            True if loaded successfully
        """
        try:
            if not self.file_path.exists():
                self.logger.debug(f"[TASK_MANAGER] No existing task file at {self.file_path}")
                self._tasks = []
                self._loaded = True
                return True
            
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            
            # Validate structure
            if not isinstance(data, dict) or "tasks" not in data:
                self.logger.warning("[TASK_MANAGER] Invalid task file format")
                self._tasks = []
                self._loaded = True
                return False
            
            self._tasks = data["tasks"]
            self._loaded = True
            
            # Log summary
            self.logger.info(f"[TASK_MANAGER] Loaded {len(self._tasks)} tasks from previous session")
            if self.pending or self.in_progress:
                self.logger.info(
                    f"[TASK_MANAGER] Status: {len(self.pending)} pending, "
                    f"{len(self.in_progress)} in progress, {len(self.completed)} completed"
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"[TASK_MANAGER] Failed to load tasks: {e}")
            self._tasks = []
            self._loaded = True
            return False
    
    def save(self) -> bool:
        """
        Save tasks to disk.
        
        Returns:
            True if saved successfully
        """
        try:
            # Ensure directory exists
            self.file_path.parent.mkdir(exist_ok=True)
            
            # Save tasks as JSON
            with open(self.file_path, 'w') as f:
                json.dump({
                    "version": "1.0",
                    "tasks": self._tasks
                }, f, indent=2)
            
            self.logger.debug(f"[TASK_MANAGER] Saved {len(self._tasks)} tasks to {self.file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"[TASK_MANAGER] Failed to save tasks: {e}")
            return False
    
    def clear(self) -> bool:
        """
        Clear all tasks and remove storage file.
        
        Returns:
            True if cleared successfully
        """
        try:
            self._tasks = []
            if self.file_path.exists():
                self.file_path.unlink()
            self.logger.debug("[TASK_MANAGER] Cleared task storage")
            return True
            
        except Exception as e:
            self.logger.error(f"[TASK_MANAGER] Failed to clear tasks: {e}")
            return False
    
    def add(self, content: str, status: str = "pending", priority: str = "medium", 
            task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Add a new task.
        
        Args:
            content: Task description
            status: Task status (pending, in_progress, completed)
            priority: Task priority (low, medium, high)
            task_id: Optional ID, will generate if not provided
            
        Returns:
            The created task
        """
        if not task_id:
            # Generate ID based on current max ID
            max_id = max([int(t["id"]) for t in self.tasks if t.get("id", "").isdigit()] + [0])
            task_id = str(max_id + 1)
        
        task = {
            "id": task_id,
            "content": content,
            "status": status,
            "priority": priority
        }
        
        self._tasks.append(task)
        self.save()
        return task
    
    def update(self, task_id: str, **updates) -> Optional[Dict[str, Any]]:
        """
        Update a task by ID.
        
        Args:
            task_id: ID of task to update
            **updates: Fields to update (content, status, priority)
            
        Returns:
            Updated task if found, None otherwise
        """
        for task in self._tasks:
            if task.get("id") == task_id:
                task.update(updates)
                self.save()
                return task
        return None
    
    def get_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by ID."""
        for task in self._tasks:
            if task.get("id") == task_id:
                return task
        return None
    
    def set_tasks(self, tasks: List[Dict[str, Any]]) -> bool:
        """
        Replace all tasks with a new list.
        
        Args:
            tasks: New task list
            
        Returns:
            True if saved successfully
        """
        self._tasks = tasks
        self._loaded = True
        return self.save()
    
    def get_summary(self) -> str:
        """
        Get a human-readable summary of tasks.
        
        Returns:
            Formatted summary string
        """
        if not self.tasks:
            return "No tasks found"
        
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
    def get_instance(cls) -> 'TaskManager':
        """Get the singleton instance of TaskManager."""
        if cls._instance is None:
            cls._instance = TaskManager()
        return cls._instance
    
    # ========== Task Display Functions (from task_display.py) ==========
    
    def build_task_hierarchy(self, state: 'KatalystState', include_progress: bool = True) -> List[str]:
        """
        Build a hierarchical view of all tasks showing parent-child relationships.
        
        Args:
            state: The current Katalyst state
            include_progress: Whether to include checkmarks for completed tasks
            
        Returns:
            List of formatted task lines
        """
        lines = []
        completed_task_names = {task[0] for task in state.completed_tasks} if include_progress else set()
        
        # Build complete task list: original plan + any new tasks from replanner
        all_tasks = []
        
        # Start with original plan if available
        if state.original_plan:
            all_tasks.extend(state.original_plan)
        
        # Add any tasks from current queue that aren't in original plan
        for task in state.task_queue:
            if task not in all_tasks:
                all_tasks.append(task)
        
        # Also include completed tasks that might not be in either list
        for task_name, _ in state.completed_tasks:
            if task_name not in all_tasks:
                all_tasks.append(task_name)
        
        # Process each task
        for task_idx, task in enumerate(all_tasks):
            task_num = task_idx + 1
            
            # Check if task is completed
            is_completed = task in completed_task_names
            marker = "✓" if is_completed and include_progress else " "
            lines.append(f"{marker} {task_num}. {task}")
        
        return lines
    
    def get_task_progress_display(self, state: 'KatalystState') -> str:
        """
        Generate a complete task progress display with header and formatting.
        
        Args:
            state: The current Katalyst state
            
        Returns:
            Formatted progress display string
        """
        # Count totals based on all tasks (original + replanned)
        # This ensures accurate count when replanner adds new tasks
        all_task_count = len(set(
            list(state.original_plan or []) + 
            list(state.task_queue) + 
            [task[0] for task in state.completed_tasks]
        ))
        total_tasks = all_task_count
        completed_count = len(state.completed_tasks)
        
        # Build display
        lines = [
            f"\n{'='*60}",
            f"=== Task Progress ({completed_count}/{total_tasks} completed) ===",
            f"{'='*60}"
        ]
        
        # Add hierarchical task list
        lines.extend(self.build_task_hierarchy(state, include_progress=True))
        
        lines.append(f"{'='*60}\n")
        
        return "\n".join(lines)


# For backward compatibility and convenience
def build_task_hierarchy(state: 'KatalystState', include_progress: bool = True) -> List[str]:
    """Build task hierarchy using TaskManager singleton."""
    return TaskManager.get_instance().build_task_hierarchy(state, include_progress)


def get_task_progress_display(state: 'KatalystState') -> str:
    """Get task progress display using TaskManager singleton."""
    return TaskManager.get_instance().get_task_progress_display(state)