from typing import Dict
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import katalyst_tool
from katalyst.katalyst_core.services.code_structure import extract_code_definitions
import json


@katalyst_tool(
    prompt_module="list_code_definitions",
    prompt_var="LIST_CODE_DEFINITION_NAMES_TOOL_PROMPT",
)
def list_code_definition_names(path: str, auto_approve: bool = True) -> str:
    """
    Lists code definitions (classes, functions, methods) from a source file or files in a directory using the tree-sitter-languages package.
    Supports Python, JavaScript, TypeScript, and TSX source files. No manual grammar setup is required.
    Returns a JSON string with keys: 'files' (list of file result objects), and optionally 'error'.
    Each file result object has: 'file', 'definitions' (list), and optionally 'info' or 'error'.
    Each definition has: 'type', 'name', 'line'.
    """
    logger = get_logger()
    logger.debug(
        f"Entered list_code_definition_names with path: {path}, auto_approve: {auto_approve}"
    )
    results = extract_code_definitions(path)
    if "error" in results:
        return json.dumps({"error": results["error"]})
    if "info" in results:
        return json.dumps({"info": results["info"], "files": []})
    files_json = []
    for fname, defs in results.items():
        file_entry = {"file": fname}
        if not defs:
            file_entry["info"] = "No definitions found."
            file_entry["definitions"] = []
        else:
            file_entry["definitions"] = []
            for d in defs:
                if "error" in d:
                    file_entry["error"] = d["error"]
                else:
                    file_entry["definitions"].append(
                        {
                            "type": d.get("type"),
                            "name": d.get("name"),
                            "line": d.get("line"),
                        }
                    )
        files_json.append(file_entry)
    logger.debug("Exiting list_code_definition_names")
    return json.dumps({"files": files_json})
