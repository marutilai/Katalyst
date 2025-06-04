from typing import Dict
from katalyst_agent.utils.logger import get_logger
from katalyst_agent.utils.tools import katalyst_tool
from katalyst_agent.utils.gitignore import load_gitignore_patterns
import os
from pathlib import Path
import pathspec
import json


def format_list_files_response(path: str, files: list = None, error: str = None) -> str:
    """
    Standardizes the output as a JSON string for downstream processing.
    """
    if error:
        return json.dumps({"path": path, "error": error})
    return json.dumps({"path": path, "files": files or []})


@katalyst_tool(prompt_module="list_files", prompt_var="LIST_FILES_PROMPT")
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
    logger.debug(f"DEBUG list_files CALLED WITH: path='{path}' (type: {type(path)}), recursive={recursive} (type: {type(recursive)}), respect_gitignore={respect_gitignore} (type: {type(respect_gitignore)})")

    if not os.path.exists(path):
        logger.error(f"Path does not exist: {path}")
        return format_list_files_response(path, error=f"Path does not exist: {path}")

    result = []
    spec = None
    if respect_gitignore:
        try:
            spec = load_gitignore_patterns(path)
        except Exception as e:
            logger.error(f"Error loading .gitignore: {e}")
            return format_list_files_response(path, error=f"Could not load .gitignore: {e}")

    if recursive:
        for root, dirs, files in os.walk(path):
            rel_root = os.path.relpath(root, path)
            # Filter dirs and files using pathspec if enabled
            if spec:
                dirs[:] = [d for d in dirs if not spec.match_file(os.path.join(rel_root, d))]
                files = [f for f in files if not spec.match_file(os.path.join(rel_root, f))]
            for name in dirs:
                result.append(os.path.normpath(os.path.join(rel_root, name)) + '/')
            for name in files:
                result.append(os.path.normpath(os.path.join(rel_root, name)))
    else:
        try:
            entries = os.listdir(path)
            if spec:
                entries = [e for e in entries if not spec.match_file(e)]
            for entry in entries:
                full_path = os.path.join(path, entry)
                if os.path.isdir(full_path):
                    result.append(entry + '/')
                else:
                    result.append(entry)
        except Exception as e:
            logger.error(f"Error listing files in {path}: {e}")
            return format_list_files_response(path, error=f"Could not list files in {path}: {e}")

    logger.debug(f"Exiting list_files with {len(result)} entries.")
    return format_list_files_response(path, files=result)
