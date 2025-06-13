import tempfile
import os
from tree_sitter_languages import get_parser
from katalyst.app.config import EXT_TO_LANG

# --- Syntax Checking Utilities ---
# This module provides syntax checking for multiple languages.
# - For Python, it uses py_compile for robust syntax validation.
# - For other supported languages (JS, TS, TSX, JSX), it uses tree-sitter for fast parse error detection.
# - The design is extensible for future language support.


def get_errors(root_node):
    """
    Walks the tree-sitter parse tree and collects error/missing nodes.
    Returns a list of dicts with node, type, start_point, end_point.
    This is used to find syntax errors or incomplete constructs in code.
    """
    errors = []
    nodes_to_visit = [root_node]
    while nodes_to_visit:
        node = nodes_to_visit.pop()
        # tree-sitter marks error/missing nodes for parse failures
        if getattr(node, "is_error", False) or getattr(node, "is_missing", False):
            errors.append(
                {
                    "node": node,
                    "type": node.type,
                    "start_point": node.start_point,  # (row, col) tuple, 0-based
                    "end_point": node.end_point,
                }
            )
        # Recursively visit all children
        nodes_to_visit.extend(reversed(node.children))
    # Sort errors by their start/end line for easier reporting
    errors.sort(key=lambda x: (x["start_point"][0], x["end_point"][0]))
    return errors


def check_syntax(content: str, file_extension: str) -> str:
    """
    Checks syntax for the given content based on file extension.
    - For Python: uses py_compile (writes to temp file, compiles, deletes temp file).
    - For other supported languages: uses tree-sitter-languages to parse and report errors with context.
    Returns an error string if any, else empty string.
    """
    # --- Python Syntax Checking ---
    if file_extension == "py":
        try:
            # Write code to a temporary file for compilation
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmpf:
                tmpf.write(content)
                tmpf.flush()
                tmp_path = tmpf.name
            import py_compile

            # py_compile will raise an exception if syntax is invalid
            py_compile.compile(tmp_path, doraise=True)
            os.remove(tmp_path)
            return ""  # No error
        except Exception as e:
            # Return the error message from the compiler
            return str(e)
    # --- Tree-sitter Syntax Checking for Other Languages ---
    # Normalize extension (with dot)
    ext = f".{file_extension}" if not file_extension.startswith(".") else file_extension
    lang_name = EXT_TO_LANG.get(ext)
    if lang_name:
        try:
            # Get the tree-sitter parser for the language
            parser = get_parser(lang_name)
            # Parse the code (tree-sitter expects bytes)
            tree = parser.parse(content.encode())
            # Find all error/missing nodes in the parse tree
            errors = get_errors(tree.root_node)
            if not errors:
                return ""  # No syntax errors found
            # --- Format error report with context ---
            # For each error, print a few lines before/after, with line numbers and error markers
            lines = content.splitlines()
            lines_to_print = set()
            errors_on_line = {}
            for error in errors:
                start_row, start_col = error["start_point"]
                end_row, end_col = error["end_point"]
                # Print 2 lines before and after the error for context
                context_start = max(0, start_row - 2)
                context_end = min(len(lines), end_row + 3)
                for i in range(context_start, context_end):
                    lines_to_print.add(i)
                # Mark the start and end lines with error info
                errors_on_line[start_row] = (
                    f"        <--- Problem here at Line {start_row + 1}:{start_col + 1}, type: {error['type']}"
                )
                if end_row != start_row:
                    errors_on_line[end_row] = (
                        f"        <--- Problem here at Line {end_row + 1}:{end_col + 1}, type: {error['type']}"
                    )
            # Build the output, showing only relevant lines and error markers
            result_output_lines = []
            last_printed_line = -1
            sorted_lines_to_print = sorted(list(lines_to_print))
            for line_num in sorted_lines_to_print:
                if line_num >= len(lines):
                    continue
                # Print a separator if skipping lines
                if line_num > last_printed_line + 1:
                    result_output_lines.append("-" * 80)
                line_content = lines[line_num]
                display_line_num = line_num + 1
                line_output = f"{display_line_num:4d} | {line_content}"
                # Add error marker if this line has an error
                if line_num in errors_on_line:
                    line_output += errors_on_line[line_num]
                result_output_lines.append(line_output)
                last_printed_line = line_num
            return "\n".join(result_output_lines)
        except Exception as e:
            # If tree-sitter fails, return a parse error message
            return f"[Tree-sitter parse error: {e}]"

    # --- Fallback for unsupported languages ---
    # TODO: Add general syntax checking for other languages (C, C++, Java, etc.)

    return ""  # No error or unsupported language
