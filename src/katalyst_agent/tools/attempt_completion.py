from typing import Dict
from katalyst_agent.utils.logger import get_logger
from katalyst_agent.utils.tools import katalyst_tool

@katalyst_tool
def attempt_completion(arguments: Dict) -> str:
    """
    Signals that the LLM believes the task is complete and presents a final result to the user.
    Expects 'result' in arguments.
    """
    logger = get_logger()
    logger.info(f"Entered attempt_completion with arguments: {arguments}")
    result = arguments.get("result", "Task completed.")
    logger.info(f"Exiting attempt_completion with result: {result}")
    return result 