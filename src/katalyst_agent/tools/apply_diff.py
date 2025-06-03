import os
import re
from katalyst_agent.utils.logger import get_logger
from katalyst_agent.utils.tools import katalyst_tool
from katalyst_agent.utils.syntax_checker import check_syntax
import tempfile

@katalyst_tool(prompt_module="apply_diff", prompt_var="APPLY_DIFF_PROMPT")
def apply_diff(path: str, diff: str, mode: str = "patch", auto_approve: bool = True) -> str:
    """
    Applies changes to a file using a specific search/replace diff format. Checks syntax before applying for Python files.
    """
    logger = get_logger()
    logger.info(f"Entered apply_diff with path: {path}, diff=<omitted>, mode: {mode}, auto_approve: {auto_approve}")

    # Validate arguments
    if not path or not diff:
        return """
<apply_diff>
<error>Both 'path' and 'diff' arguments are required.</error>
</apply_diff>"""
    if not os.path.isfile(path):
        return f"""
<apply_diff>
<error>File not found: {path}</error>
</apply_diff>"""

    # Read the original file
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Parse all diff blocks (support multi-block)
    diff_blocks = re.findall(r"<<<<<<< SEARCH(.*?)>>>>>>> REPLACE", diff, re.DOTALL)
    if not diff_blocks:
        return """
<apply_diff>
<error>No valid diff blocks found. Please use the correct format.</error>
</apply_diff>"""

    new_lines = lines[:]
    offset = 0  # Track line number changes due to previous replacements
    for block in diff_blocks:
        # Extract start_line
        m = re.search(r":start_line:(\d+)[\r\n]+-------([\s\S]*?)=======([\s\S]*)", block)
        if not m:
            return """
<apply_diff>
<error>Malformed diff block. Each block must have :start_line, -------, and =======.</error>
</apply_diff>"""
        start_line = int(m.group(1))
        search_content = m.group(2).strip('\n')
        replace_content = m.group(3).strip('\n')
        # Compute 0-based indices
        s_idx = start_line - 1 + offset
        search_lines = [l.rstrip('\r\n') for l in search_content.splitlines()]
        replace_lines = [l.rstrip('\r\n') for l in replace_content.splitlines()]
        # Check if the search block matches
        if new_lines[s_idx:s_idx+len(search_lines)] != [l + '\n' for l in search_lines]:
            return f"""
<apply_diff>
<error>Search block does not match file at line {start_line}. Please use read_file to get the exact content and line numbers.</error>
</apply_diff>"""
        # Apply the replacement
        new_lines[s_idx:s_idx+len(search_lines)] = [l + '\n' for l in replace_lines]
        # Update offset for subsequent blocks
        offset += len(replace_lines) - len(search_lines)

    # Preview the diff for the user
    print(f"\n# Katalyst is about to apply the following diff to '{os.path.abspath(path)}':")
    print("-" * 80)
    for i, line in enumerate(new_lines, 1):
        print(f"{i:4d} | {line.rstrip()}")
    print("-" * 80)

    # Check syntax for Python files
    if path.endswith('.py'):
        file_extension = path.split('.')[-1]
        syntax_error = check_syntax(''.join(new_lines), file_extension)
        if syntax_error:
            return f"""
<apply_diff>
<error>Syntax error after applying diff: {syntax_error}</error>
</apply_diff>"""

    # Confirm with user unless auto_approve is True
    if not auto_approve:
        confirm = input(f"Proceed with applying diff to '{path}'? (y/n): ").strip().lower()
        if confirm != 'y':
            logger.info("User declined to apply diff.")
            return "<apply_diff>\n<info>User declined to apply diff.</info>\n</apply_diff>"

    # Write the new file
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        logger.info(f"Successfully applied diff to file: {path}")
        logger.info("Exiting apply_diff")
        return f"<apply_diff>\n<info>Successfully applied diff to file: {path}</info>\n</apply_diff>"
    except Exception as e:
        logger.error(f"Error writing to file {path}: {e}")
        logger.info("Exiting apply_diff")
        return f"<apply_diff>\n<error>Could not write to file {path}: {e}</error>\n</apply_diff>"
