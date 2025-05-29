from katalyst_agent.utils.logger import get_logger
from katalyst_agent.utils.tools import katalyst_tool
import os
from katalyst_agent.utils.gitignore import load_gitignore_patterns

@katalyst_tool
def read_file(path: str, start_line: int = None, end_line: int = None, mode: str = None, auto_approve: bool = True, respect_gitignore: bool = True) -> str:
    """
    Reads the content of a file, optionally from a specific start line to an end line (1-based, inclusive).
    Returns a structured XML-style result for downstream agent parsing.
    Only the required lines are read into memory (streaming approach).
    """
    logger = get_logger()
    logger.info(f"Entered read_file with path={path}, start_line={start_line}, end_line={end_line}, mode={mode}, auto_approve={auto_approve}, respect_gitignore={respect_gitignore}")

    # Validate path argument
    if not path or not isinstance(path, str):
        logger.error("No valid 'path' provided to read_file.")
        return f"""
<read_file>
<error>No valid 'path' provided.</error>
</read_file>"""

    abs_path = os.path.abspath(path)
    if not os.path.isfile(abs_path):
        logger.error(f"File not found: {abs_path}")
        return f"""
<read_file>
<error>File not found: {abs_path}</error>
</read_file>"""

    # Respect .gitignore if requested (prevents reading ignored/sensitive files)
    if respect_gitignore:
        try:
            spec = load_gitignore_patterns(os.path.dirname(abs_path) or '.')
            rel_path = os.path.relpath(abs_path, os.path.dirname(abs_path) or '.')
            if spec and spec.match_file(rel_path):
                logger.error(f"Permission denied to read the file '{abs_path}' due to .gitignore.")
                return f"""
<read_file>
<error>Permission denied to read the file '{abs_path}' due to .gitignore.</error>
</read_file>"""
        except Exception as e:
            logger.error(f"Error loading .gitignore: {e}")
            return f"""
<read_file>
<error>Could not load .gitignore: {e}</error>
</read_file>"""

    # --- Streaming line selection logic ---
    # If no start_line/end_line provided, default to full file
    # start_line is 1-based (first line is 1), so s_idx is 0-based
    s_idx = (start_line - 1) if start_line and start_line > 0 else 0
    # end_line is inclusive, so we use < e_idx in the loop
    e_idx = end_line if end_line and end_line > 0 else float('inf')
    selected_lines = []
    last_line_num = s_idx
    try:
        with open(abs_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                # Skip lines before start_line
                if i < s_idx:
                    continue
                # Stop after end_line (inclusive)
                if i >= e_idx:
                    break
                selected_lines.append(line)
                last_line_num = i
    except Exception as e:
        logger.error(f"Error reading file {abs_path}: {e}")
        return f"""
<read_file>
<error>Could not read file {abs_path}: {e}</error>
</read_file>"""

    # Print preview for user (not returned to agent)
    print(f"\n# Katalyst is about to read the following content from '{abs_path}':")
    print("-" * 80)
    for idx, line in enumerate(selected_lines, start=s_idx + 1):
        print(f"{idx:4d} | {line.rstrip()}")
    print("-" * 80)

    logger.info(f"Read {len(selected_lines)} lines from file: {abs_path}")
    logger.info("Exiting read_file")

    # If no lines were selected, return an info message in XML
    if not selected_lines:
        return f"""
<read_file>
<file>
<path>{abs_path}</path>
<content lines="{s_idx+1}-{last_line_num+1}">[INFO] File is empty or no lines in specified range.</content>
</file>
</read_file>"""

    # Join selected lines for XML output
    file_contents = ''.join(selected_lines)
    return f"""
<read_file>
<file>
<path>{abs_path}</path>
<content lines="{s_idx+1}-{last_line_num+1}">
{file_contents}</content>
</file>
</read_file>"""
