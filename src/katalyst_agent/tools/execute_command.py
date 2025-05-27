from typing import Dict
from katalyst_agent.utils.logger import get_logger
from katalyst_agent.utils.tools import katalyst_tool


@katalyst_tool
def execute_command(
    arguments: Dict, mode: str = "code", auto_approve: bool = False
) -> str:
    """
    Executes a shell command in the terminal.
    """
    logger = get_logger()
    logger.info(
        f"Entered execute_command with arguments: {arguments}, mode: {mode}, auto_approve: {auto_approve}"
    )
    pass
    logger.info("Exiting execute_command")
