import os
import json
from src.app.config import KATALYST_STATE_FILE
from src.katalyst_core.utils.logger import get_logger
from langchain_core.messages import message_to_dict, messages_from_dict


def load_project_state():
    if os.path.exists(KATALYST_STATE_FILE):
        try:
            with open(KATALYST_STATE_FILE, "r") as f:
                state = json.load(f)
                # If chat_history is present and is a list of dicts, deserialize it
                if "chat_history" in state and isinstance(state["chat_history"], list):
                    # Only convert if items look like message dicts
                    if (
                        state["chat_history"]
                        and isinstance(state["chat_history"][0], dict)
                        and "type" in state["chat_history"][0]
                    ):
                        state["chat_history"] = messages_from_dict(
                            state["chat_history"]
                        )
                return state
        except Exception:
            return {}
    return {}


def save_project_state(state):
    logger = get_logger()
    try:
        # If chat_history is present and is a list of BaseMessage, serialize it
        state_to_save = dict(state)
        if "chat_history" in state_to_save and isinstance(
            state_to_save["chat_history"], list
        ):
            state_to_save["chat_history"] = [
                message_to_dict(m) if hasattr(m, "type") else m
                for m in state_to_save["chat_history"]
            ]
        with open(KATALYST_STATE_FILE, "w") as f:
            json.dump(state_to_save, f)
    except Exception as e:
        logger.error(f"Failed to save project state to {KATALYST_STATE_FILE}: {e}")
