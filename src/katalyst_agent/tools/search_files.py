from typing import Dict
from katalyst_agent.utils.logger import get_logger
from katalyst_agent.utils.tools import katalyst_tool


@katalyst_tool
def regex_search_files(arguments: Dict, auto_approve: bool = False) -> str:
    """
    Performs a regex search across files in a directory using ripgrep.
    """
    logger = get_logger()
    logger.info(
        f"Entered regex_search_files with arguments: {arguments}, auto_approve: {auto_approve}"
    )
    pass
    logger.info("Exiting regex_search_files")
