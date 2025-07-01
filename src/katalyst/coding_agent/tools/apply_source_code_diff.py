import os
import re
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import katalyst_tool
from katalyst.katalyst_core.utils.syntax_checker import check_syntax
from katalyst.katalyst_core.utils.fuzzy_match import find_fuzzy_match_in_lines
import json


def format_apply_source_code_diff_response(
    path: str, success: bool, info: str = None, error: str = None
) -> str:
    """
    Standardizes the output as a JSON string for downstream processing.
    """
    resp = {"path": path, "success": success}
    if info:
        resp["info"] = info
    if error:
        resp["error"] = error
    return json.dumps(resp)


@katalyst_tool(
    prompt_module="apply_source_code_diff", prompt_var="APPLY_SOURCE_CODE_DIFF_TOOL_PROMPT"
)
def apply_source_code_diff(
    path: str, diff: str, auto_approve: bool = True, user_input_fn=None,
    fuzzy_buffer_size: int = 20, fuzzy_threshold: int = 95
) -> str:
    """
    Applies changes to a file using a specific search/replace diff format. Checks syntax before applying for Python files.
    Supports fuzzy matching when exact match fails.
    Returns a JSON string with keys: 'path', 'success', and either 'info' or 'error'.
    Parameters:
      - path: str (file to modify)
      - diff: str (search/replace block(s))
      - auto_approve: bool (skip confirmation prompt if True)
      - fuzzy_buffer_size: int (number of lines to search around start_line for fuzzy match)
      - fuzzy_threshold: int (minimum similarity score for fuzzy match, 0-100)
    """
    logger = get_logger()
    logger.debug(
        f"Entered apply_source_code_diff with path: {path}, diff=<omitted>, auto_approve: {auto_approve}"
    )

    # Validate arguments
    if not path or not diff:
        return format_apply_source_code_diff_response(
            path or "", False, error="Both 'path' and 'diff' arguments are required."
        )
    if not os.path.isfile(path):
        return format_apply_source_code_diff_response(
            path, False, error=f"File not found: {path}"
        )

    # Read the original file
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Parse all diff blocks (support multi-block)
    diff_blobs = re.findall(r"<<<<<<< SEARCH(.*?)>>>>>>> REPLACE", diff, re.DOTALL)
    if not diff_blobs:
        return format_apply_source_code_diff_response(
            path,
            False,
            error="No valid diff blocks found. Please use the correct format.",
        )

    # Parse each diff blob to extract metadata and content into a structured list.
    # This makes it easier to sort and process them reliably.
    parsed_blocks = []
    for blob in diff_blobs:
        match = re.search(
            r":start_line:(\d+)[\r\n]+-------([\s\S]*?)=======([\s\S]*)", blob
        )
        if not match:
            # Check if they forgot the ------- separator
            if ":start_line:" in blob and "-------" not in blob:
                error_msg = (
                    "Missing '-------' separator after :start_line:. "
                    "The format MUST be:\n"
                    ":start_line:<number>\n"
                    "-------\n"
                    "<search content>"
                )
            else:
                error_msg = "Malformed diff block. Each block must have :start_line:, -------, and =======."
            
            return format_apply_source_code_diff_response(
                path,
                False,
                error=error_msg,
            )
        parsed_blocks.append(
            {
                "start_line": int(match.group(1)),
                "search_content": match.group(2).strip("\n"),
                "replace_content": match.group(3).strip("\n"),
            }
        )

    # Sort blocks in reverse order of start_line.
    # By applying changes from the bottom of the file upwards, we ensure that
    # line numbers for subsequent (earlier) blocks remain correct without needing
    # to track index offsets.
    parsed_blocks.sort(key=lambda b: b["start_line"], reverse=True)

    new_lines = lines[:]
    for block in parsed_blocks:
        start_line = block["start_line"]
        search_content = block["search_content"]
        replace_content = block["replace_content"]

        s_idx = start_line - 1  # Compute 0-based index
        search_lines = [l.rstrip("\r\n") for l in search_content.splitlines()]
        replace_lines = [l.rstrip("\r\n") for l in replace_content.splitlines()]

        # Check if the search block matches the content at the specified line
        exact_match = True
        if new_lines[s_idx : s_idx + len(search_lines)] != [
            l + "\n" for l in search_lines
        ]:
            exact_match = False
            
            # Try fuzzy matching
            logger.info(
                f"Exact match failed at line {start_line}. Attempting fuzzy match..."
            )
            fuzzy_result = find_fuzzy_match_in_lines(
                new_lines, search_lines, start_line, fuzzy_buffer_size, fuzzy_threshold
            )
            
            if fuzzy_result is None:
                return format_apply_source_code_diff_response(
                    path,
                    False,
                    error=f"Search block does not match file at line {start_line} (exact match failed). "
                          f"Fuzzy search within +/- {fuzzy_buffer_size} lines also failed "
                          f"(no match with >= {fuzzy_threshold}% similarity). "
                          f"Please use read_file to get the exact content and line numbers.",
                )
            
            # Update the index to the fuzzy match location
            s_idx, similarity = fuzzy_result
            logger.info(
                f"Fuzzy match found at line {s_idx + 1} with {similarity:.1f}% similarity"
            )

        # Apply the replacement
        new_lines[s_idx : s_idx + len(search_lines)] = [l + "\n" for l in replace_lines]
        
        # Log whether this was an exact or fuzzy match
        if exact_match:
            logger.debug(f"Applied exact match replacement at line {s_idx + 1}")
        else:
            logger.debug(f"Applied fuzzy match replacement at line {s_idx + 1}")

    # Preview the diff for the user
    print(
        f"\n# Katalyst is about to apply the following diff to '{os.path.abspath(path)}':"
    )
    print("-" * 80)
    for i, line in enumerate(new_lines, 1):
        print(f"{i:4d} | {line.rstrip()}")
    print("-" * 80)

    # Check syntax for Python files
    if path.endswith(".py"):
        file_extension = path.split(".")[-1]
        syntax_error = check_syntax("".join(new_lines), file_extension)
        if syntax_error:
            return format_apply_source_code_diff_response(
                path, False, error=f"Syntax error after applying diff: {syntax_error}"
            )

    # Confirm with user unless auto_approve is True
    if not auto_approve:
        if user_input_fn is None:
            user_input_fn = input
        confirm = (
            user_input_fn(f"Proceed with applying diff to '{path}'? (y/n) [y]: ")
            .strip()
            .lower()
        ) or "y"
        if confirm != "y":
            logger.info("User declined to apply diff.")
            return format_apply_source_code_diff_response(
                path, False, info="User declined to apply diff."
            )

    # Write the new file
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        logger.info(f"Successfully applied diff to file: {path}")
        logger.debug("Exiting apply_source_code_diff")
        return format_apply_source_code_diff_response(
            path, True, info=f"Successfully applied diff to file: {path}"
        )
    except Exception as e:
        logger.error(f"Error writing to file {path}: {e}")
        logger.debug("Exiting apply_source_code_diff")
        return format_apply_source_code_diff_response(
            path, False, error=f"Could not write to file {path}: {e}"
        )
