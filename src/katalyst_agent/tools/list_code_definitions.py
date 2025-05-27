from typing import Dict
from katalyst_agent.utils.logger import get_logger
from katalyst_agent.utils.tools import katalyst_tool


@katalyst_tool
def list_code_definition_names(arguments: Dict, auto_approve: bool = False) -> str:
    """
    Lists code definitions (classes, functions, methods) from a source file or files in a directory using Tree-sitter.
    """
    logger = get_logger()
    logger.info(
        f"Entered list_code_definitions with arguments: {arguments}, auto_approve: {auto_approve}"
    )
    pass
    logger.info("Exiting list_code_definitions")
