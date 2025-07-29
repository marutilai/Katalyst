"""
Utilities for parsing task types from task strings and mapping to playbook content.
"""

import re
from pathlib import Path
from typing import Optional, Tuple
from katalyst.katalyst_core.utils.models import TaskType


def _load_playbook_content(playbook_name: str) -> str:
    """
    Load playbook content from the playbook hub.

    Args:
        playbook_name: Name of the playbook file (without .md extension)

    Returns:
        Content of the playbook or empty string if not found
    """
    # Get the path to the playbook
    playbook_path = (
        Path(__file__).parent.parent.parent / "playbook_hub" / f"{playbook_name}.md"
    )

    try:
        if playbook_path.exists():
            return playbook_path.read_text()
        else:
            return ""
    except Exception:
        return ""


def parse_task_type(task: str) -> Tuple[Optional[TaskType], str]:
    """
    Parse task type from a task string prefixed with [TYPE].

    Args:
        task: Task string, potentially prefixed with [TYPE]

    Returns:
        Tuple of (TaskType or None, cleaned task description)
    """
    # Pattern to match [TYPE] at the beginning of the string
    pattern = r"^\[([A-Z_]+)\]\s*(.*)$"
    match = re.match(pattern, task.strip())

    if match:
        type_str = match.group(1)
        description = match.group(2)

        # Try to convert to TaskType enum
        try:
            task_type = TaskType(type_str.lower())
            return task_type, description
        except ValueError:
            # Invalid task type, treat as OTHER
            return TaskType.OTHER, description

    # No type prefix found
    return None, task


def get_task_type_guidance(task_type: TaskType) -> str:
    """
    Get specialized guidance for a given task type.

    Args:
        task_type: The TaskType enum value

    Returns:
        Specialized guidance string for the task type
    """
    guidance_map = {
        TaskType.TEST_CREATION: _load_playbook_content("test_creation"),
        TaskType.FEATURE_ENGINEERING: _load_playbook_content("feature_engineering"),
        TaskType.DATA_EXPLORATION: _load_playbook_content("data_exploration"),
        # TaskType.REFACTOR: _load_playbook_content("refactor"),
        # TaskType.DOCUMENTATION: _load_playbook_content("documentation"),
        # TaskType.MODEL_TRAINING: _load_playbook_content("model_training"),
        # TaskType.MODEL_EVALUATION: _load_playbook_content("model_evaluation"),
    }

    return guidance_map.get(task_type, "")
