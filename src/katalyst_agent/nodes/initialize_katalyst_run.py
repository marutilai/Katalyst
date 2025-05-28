from typing import Any, Dict, Union
from pydantic import ValidationError
from katalyst_agent.state import KatalystAgentState
from katalyst_agent.utils.logger import get_logger
import copy


def initialize_katalyst_run(initial_state: Union[Dict[str, Any], KatalystAgentState]) -> KatalystAgentState:
    """
    Initializes the KatalystAgentState for a new run using the Pydantic model.
    Populates required fields, initializes chat_history and current_iteration, and sets optional fields to defaults/None.
    """
    logger = get_logger()
    # Print iteration number (0 for initialization)
    logger.info(f"Entered initialize_katalyst_run (iteration 0)")
    logger.debug(f"State: {initial_state}")
    state_before = None
    chat_history_before = []
    # If already a KatalystAgentState, just return it
    if isinstance(initial_state, KatalystAgentState):
        logger.debug("Input is already a KatalystAgentState, returning as is.")
        logger.info("Exiting initialize_katalyst_run (iteration 0)")
        return initial_state
    try:
        state = KatalystAgentState(
            task=initial_state.get("task"),
            current_mode=initial_state.get("current_mode"),
            llm_provider=initial_state.get("llm_provider"),
            llm_model_name=initial_state.get("llm_model_name"),
            auto_approve=initial_state.get("auto_approve", False),
            max_iterations=initial_state.get("max_iterations", 10),
            current_iteration=initial_state.get("current_iteration", 0),
            # All other fields will use Pydantic defaults
        )
    except ValidationError as e:
        raise ValueError(f"Invalid initial state for KatalystAgentState: {e}")
    # Log only changed fields (all fields, since this is initialization)
    changed = state.dict()
    if "chat_history" in changed:
        changed["chat_history"] = state.chat_history[len(chat_history_before):]
    logger.info(f"initialize_katalyst_run set state: {changed}")
    logger.info("Exiting initialize_katalyst_run (iteration 0)")
    return state
 