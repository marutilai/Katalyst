import os
import subprocess
from katalyst_agent.utils.logger import get_logger
from katalyst_agent.utils.tools import katalyst_tool
from shutil import which
from katalyst_agent.config import SEARCH_FILES_MAX_RESULTS  # Centralized config

@katalyst_tool
def regex_search_files(path: str, regex: str, file_pattern: str = None, auto_approve: bool = True) -> str:
    """
    Performs a regex search across files in a directory using ripgrep (rg).
    Parameters:
      - path: str (directory to search in)
      - regex: str (pattern to search for)
      - file_pattern: str (optional glob pattern to filter files)
      - auto_approve: bool (default True)
    Returns XML-style results. Limits output to SEARCH_FILES_MAX_RESULTS for readability.
    """
    logger = get_logger()
    logger.info(f"Entered regex_search_files with path: {path}, regex: {regex}, file_pattern: {file_pattern}, auto_approve: {auto_approve}")

    # Check for required arguments
    if not path or not regex:
        return """
<search_files>
<error>Both 'path' and 'regex' arguments are required.</error>
</search_files>"""

    # Check if the provided path is a valid directory
    if not os.path.isdir(path):
        return f"""
<search_files>
<error>Directory not found: {path}</error>
</search_files>"""

    # Check if ripgrep (rg) is installed and available in PATH
    if which("rg") is None:
        return """
<search_files>
<error>'rg' (ripgrep) is not installed.</error>
</search_files>"""

    # Build the ripgrep command
    # --with-filename: always print the file name for each match
    # --line-number: print the line number for each match
    # --color never: disable color codes for easier parsing
    # regex: the pattern to search for
    # path: the directory to search in
    cmd = ["rg", "--with-filename", "--line-number", "--color", "never", regex, path]

    # If a file pattern is provided, add it as a --glob argument
    if file_pattern:
        cmd.extend(["--glob", file_pattern])

    # Limit output for safety and performance
    # --max-filesize 1M: skip files larger than 1MB
    # --max-count 1000: stop after 1000 matches
    cmd.extend(["--max-filesize", "1M", "--max-count", str(SEARCH_FILES_MAX_RESULTS)])

    # Add context lines and custom separator for richer output
    # --context 2: include 2 lines before and after each match
    # --context-separator -----: use '-----' to separate context blocks
    cmd.extend(["--context", "2", "--context-separator", "-----"])

    # Exclude common junk directories and files
    cmd.extend(["-g", "!node_modules/**", "-g", "!__pycache__/**", "-g", "!.env", "-g", "!.git/**"])

    try:
        # Run the ripgrep command and capture output
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        # This should not happen due to the earlier which() check, but handle just in case
        return """
<search_files>
<error>ripgrep (rg) is not installed. Please install it to use this tool.</error>
</search_files>"""

    output = result.stdout.strip()

    # If no matches are found, return an info message
    if not output:
        return f"""
<search_files>
<info>No matches found for pattern '{regex}' in {path}.</info>
</search_files>"""

    # Parse the output: each line is 'file:line:match' or a context line
    xml = ["<search_files>"]
    match_count = 0
    for line in output.splitlines():
        # Try to split into file, line, and content
        parts = line.split(":", 2)
        if len(parts) == 3:
            fname, lineno, content = parts
            # Each match is wrapped in a <match> tag with file and line attributes
            xml.append(f"  <match file=\"{fname}\" line=\"{lineno}\">{content}</match>")
            match_count += 1
            if match_count >= SEARCH_FILES_MAX_RESULTS:
                break
        else:
            # Context or separator lines are wrapped in <raw> tags
            xml.append(f"  <raw>{line}</raw>")
    if match_count >= SEARCH_FILES_MAX_RESULTS:
        xml.append(f"  <info>Results truncated at {SEARCH_FILES_MAX_RESULTS} matches.</info>")
    xml.append("</search_files>")
    logger.info("Exiting regex_search_files")
    return '\n'.join(xml)
