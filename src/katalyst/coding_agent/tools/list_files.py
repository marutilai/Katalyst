from typing import Dict, Optional
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import katalyst_tool
from katalyst.katalyst_core.utils.file_utils import filter_paths, should_ignore_path
from katalyst.katalyst_core.utils.error_handling import create_error_message, ErrorType
from katalyst.katalyst_core.utils.directory_cache import DirectoryCache
import os
from pathlib import Path
import pathspec
import json


def format_list_files_response(path: str, files: list = None, error: str = None) -> str:
    """
    Standardizes the output as a JSON string for downstream processing.
    """
    response = {"path": path}
    if files is not None:
        response["files"] = files
    if error is not None:
        response["error"] = error
    return json.dumps(response)


@katalyst_tool(prompt_module="list_files", prompt_var="LIST_FILES_TOOL_PROMPT")
def list_files(path: str, recursive: bool, respect_gitignore: bool = True) -> str:
    """
    Lists files and directories within a given path, with options for recursion and respecting .gitignore.
    Arguments:
      - path: str (directory to list)
      - recursive: bool (True for recursive, False for top-level only)
      - respect_gitignore: bool (default True)
    Returns a JSON string with keys: 'path' (input path), 'files' (list of found files/dirs), or 'error'.
    """
    logger = get_logger()

    if not os.path.exists(path):
        logger.error(f"Path does not exist: {path}")
        return format_list_files_response(path, error=f"Path does not exist: {path}")

    result = []
    if recursive:
        for root, dirs, files in os.walk(path):
            rel_root = os.path.relpath(root, path)

            # Filter directories before walking into them
            dirs[:] = [
                d
                for d in dirs
                if not should_ignore_path(
                    os.path.join(rel_root, d), path, respect_gitignore
                )
            ]

            # Add filtered directories
            for name in dirs:
                result.append(os.path.normpath(os.path.join(rel_root, name)) + "/")

            # Add filtered files
            for name in files:
                full_path = os.path.normpath(os.path.join(rel_root, name))
                if not should_ignore_path(full_path, path, respect_gitignore):
                    result.append(full_path)
    else:
        try:
            entries = os.listdir(path)
            for entry in entries:
                full_path = os.path.join(path, entry)
                if not should_ignore_path(full_path, path, respect_gitignore):
                    if os.path.isdir(full_path):
                        result.append(entry + "/")
                    else:
                        result.append(entry)
        except Exception as e:
            logger.error(f"Error listing files in {path}: {e}")
            return format_list_files_response(
                path, error=f"Could not list files in {path}: {e}"
            )

    # Sort for consistent output
    result.sort()
    return format_list_files_response(path, files=result)
