from typing import Dict
from katalyst_agent.utils.logger import get_logger
from katalyst_agent.utils.tools import katalyst_tool


@katalyst_tool
def read_file(arguments: Dict, auto_approve: bool = False) -> str:
    """
    Reads the content of a file, optionally from a specific start line to an end line.
    """
    logger = get_logger()
    logger.info(
        f"Entered read_file with arguments: {arguments}, auto_approve: {auto_approve}"
    )
    pass
    logger.info("Exiting read_file")
