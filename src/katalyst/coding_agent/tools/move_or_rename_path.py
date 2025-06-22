import os
import shutil
import json
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import katalyst_tool


def format_move_or_rename_path_response(
    source_path: str,
    destination_path: str,
    success: bool,
    info: str = None,
    error: str = None,
) -> str:
    """
    Standardizes the output as a JSON string for downstream processing.
    """
    resp = {
        "source_path": source_path,
        "destination_path": destination_path,
        "success": success,
    }
    if info:
        resp["info"] = info
    if error:
        resp["error"] = error
    return json.dumps(resp)


@katalyst_tool(
    prompt_module="move_or_rename_path", prompt_var="MOVE_OR_RENAME_PATH_PROMPT"
)
def move_or_rename_path(source_path: str, destination_path: str) -> str:
    """
    Renames or moves a file or directory from a source path to a destination path.

    - To rename a file or directory, provide the new name in the destination_path.
      Example: move_or_rename_path('old_name.txt', 'new_name.txt')
    - To move a file or directory, provide the new directory path in the destination_path.
      Example: move_or_rename_path('file.txt', 'new_dir/')

    Args:
        source_path (str): The path of the file or directory to move/rename.
        destination_path (str): The destination path or new name.

    Returns:
        str: A JSON string with keys: 'source_path', 'destination_path', 'success', and either 'info' or 'error'.
    """
    logger = get_logger()
    logger.debug(
        f"Entered move_or_rename_path with source: {source_path}, destination: {destination_path}"
    )

    if not source_path or not destination_path:
        return format_move_or_rename_path_response(
            source_path or "",
            destination_path or "",
            False,
            error="Both 'source_path' and 'destination_path' arguments are required.",
        )

    if not os.path.exists(source_path):
        return format_move_or_rename_path_response(
            source_path,
            destination_path,
            False,
            error=f"Source path does not exist: {source_path}",
        )

    if os.path.exists(destination_path):
        # If the destination is a directory, this is a valid move operation.
        # shutil.move handles this case. Otherwise, it's a conflict.
        if not os.path.isdir(destination_path):
            return format_move_or_rename_path_response(
                source_path,
                destination_path,
                False,
                error=f"Destination path already exists and is not a directory: {destination_path}",
            )

    try:
        shutil.move(source_path, destination_path)
        logger.info(f"Successfully moved '{source_path}' to '{destination_path}'")
        return format_move_or_rename_path_response(
            source_path,
            destination_path,
            True,
            info=f"Successfully moved '{source_path}' to '{destination_path}'",
        )
    except Exception as e:
        logger.error(
            f"Error moving '{source_path}' to '{destination_path}': {e}", exc_info=True
        )
        return format_move_or_rename_path_response(
            source_path,
            destination_path,
            False,
            error=f"Could not move '{source_path}' to '{destination_path}': {e}",
        )
