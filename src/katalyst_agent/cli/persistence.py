import os
import json
from katalyst_agent.config import STATE_FILE
from katalyst_agent.utils.logger import get_logger

def load_project_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_project_state(state):
    logger = get_logger()
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        logger.error(f"Failed to save project state to {STATE_FILE}: {e}") 