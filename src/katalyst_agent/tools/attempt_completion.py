from katalyst_agent.utils.logger import get_logger
from katalyst_agent.utils.tools import katalyst_tool

@katalyst_tool(prompt_module="attempt_completion", prompt_var="ATTEMPT_COMPLETION_PROMPT")
def attempt_completion(result: str) -> str:
    """
    Presents the final result of the task to the user. Only use this after confirming all previous tool uses were successful.
    Parameters:
      - result: str (the final result description)
    Returns the result string for display to the user.
    """
    logger = get_logger()
    logger.info(f"Entered attempt_completion with result: {result}")
    if not result or not isinstance(result, str):
        logger.error("No valid 'result' provided to attempt_completion.")
        return "[ERROR] No result provided."
    logger.info("Exiting attempt_completion")
    return result 