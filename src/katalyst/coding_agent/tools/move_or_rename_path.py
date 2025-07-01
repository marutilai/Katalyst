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
    prompt_module="move_or_rename_path", prompt_var="MOVE_OR_RENAME_PATH_TOOL_PROMPT"
)
def move_or_rename_path(source_path: str, destination_path: str) -> str:
    """
    Renames or moves a file or directory. This tool automatically sanitizes
    filenames (e.g., replaces spaces with underscores) and preserves file
    extensions unless a new extension is explicitly provided.

    - To rename, provide the new name in `destination_path`.
    - To move, provide the target directory in `destination_path`.

    Args:
        source_path (str): The path of the file or directory to move/rename.
        destination_path (str): The destination path or new name.

    Returns:
        str: A JSON string with operation details.
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

    # Determine final destination path with sanitization and extension preservation
    final_destination_path = destination_path
    source_filename = os.path.basename(source_path)

    if os.path.isdir(destination_path):
        # Moving into a directory: sanitize the source filename
        sanitized_filename = source_filename.replace(" ", "_")
        final_destination_path = os.path.join(destination_path, sanitized_filename)
    else:
        # Renaming a file or directory
        dest_dir, dest_filename = os.path.split(destination_path)
        sanitized_filename = dest_filename.replace(" ", "_")

        # Preserve extension if the source is a file and destination has no extension
        if os.path.isfile(source_path):
            _, source_ext = os.path.splitext(source_filename)
            if source_ext and not os.path.splitext(sanitized_filename)[1]:
                sanitized_filename += source_ext

        final_destination_path = os.path.join(dest_dir, sanitized_filename)

    if (
        os.path.exists(final_destination_path)
        and final_destination_path != destination_path
    ):
        # If the sanitized path exists and is different from the original intent, abort.
        # This prevents overwriting a file unexpectedly due to sanitization.
        return format_move_or_rename_path_response(
            source_path,
            destination_path,
            False,
            error=f"Sanitized destination path '{final_destination_path}' already exists.",
        )

    if os.path.exists(destination_path) and not os.path.isdir(destination_path):
        return format_move_or_rename_path_response(
            source_path,
            destination_path,
            False,
            error=f"Destination path already exists and is not a directory: {destination_path}",
        )

    try:
        shutil.move(source_path, final_destination_path)
        logger.info(f"Successfully moved '{source_path}' to '{final_destination_path}'")
        return format_move_or_rename_path_response(
            source_path,
            final_destination_path,
            True,
            info=f"Successfully moved '{source_path}' to '{final_destination_path}'",
        )
    except Exception as e:
        logger.error(
            f"Error moving '{source_path}' to '{final_destination_path}': {e}",
            exc_info=True,
        )
        return format_move_or_rename_path_response(
            source_path,
            final_destination_path,
            False,
            error=f"Could not move '{source_path}' to '{final_destination_path}': {e}",
        )
