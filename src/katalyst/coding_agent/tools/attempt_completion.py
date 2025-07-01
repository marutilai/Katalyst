from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import katalyst_tool
import json


def format_attempt_completion_response(
    success: bool, result: str = None, error: str = None
) -> str:
    """
    Standardizes the output as a JSON string for downstream processing.
    """
    resp = {"success": success}
    if result:
        resp["result"] = result
    if error:
        resp["error"] = error
    return json.dumps(resp)


@katalyst_tool(
    prompt_module="attempt_completion", prompt_var="ATTEMPT_COMPLETION_TOOL_PROMPT"
)
def attempt_completion(result: str) -> str:
    """
    Presents the final result of the task to the user. Only use this after confirming all previous tool uses were successful.
    Parameters:
      - result: str (the final result description)
    Returns a JSON string with keys: 'success', 'result' (optional), and 'error' (optional).
    """
    logger = get_logger()
    logger.debug(f"Entered attempt_completion with result: {result}")
    if not result or not isinstance(result, str):
        logger.error("No valid 'result' provided to attempt_completion.")
        return format_attempt_completion_response(False, error="No result provided.")
    logger.debug("Exiting attempt_completion")
    return format_attempt_completion_response(True, result=result)
