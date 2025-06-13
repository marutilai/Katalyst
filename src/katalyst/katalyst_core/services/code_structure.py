import os
from typing import List, Dict, Union
from tree_sitter_languages import get_parser
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.file_utils import load_gitignore_patterns
from katalyst.app.config import EXT_TO_LANG


def extract_code_definitions(path: str) -> Dict:
    """
    Given a file or directory path, extract code definitions (classes, functions, methods).
    Supports Python, JavaScript, TypeScript, TSX.
    Returns a dict: {filename: [definitions]}
    Respects .gitignore when listing files in a directory.
    """
    logger = get_logger()
    logger.debug(f"Extracting code definitions from: {path}")
    if not os.path.exists(path):
        logger.error(f"Path does not exist: {path}")
        return {"error": f"Path does not exist: {path}"}
    results = {}

    def extract_defs_for_file(fpath, ext):
        lang_name = EXT_TO_LANG.get(ext)
        if not lang_name:
            return [{"error": f"Unsupported file type: {ext}"}]
        try:
            parser = get_parser(lang_name)
        except Exception as e:
            return [{"error": f"Could not load language parser for {lang_name}: {e}"}]
        with open(fpath, "r", encoding="utf-8") as f:
            code = f.read()
        tree = parser.parse(code.encode())
        root = tree.root_node
        results_list = []

        def visit(node):
            # Python: function_definition, class_definition
            # JS/TS: function_declaration, class_declaration, method_definition
            if lang_name == "python" and node.type in (
                "function_definition",
                "class_definition",
            ):
                name = None
                for child in node.children:
                    if child.type == "identifier":
                        name = code[child.start_byte : child.end_byte]
                        break
                if name:
                    results_list.append(
                        {
                            "name": name,
                            "type": "class"
                            if node.type == "class_definition"
                            else "function",
                            "line": node.start_point[0] + 1,
                        }
                    )
            elif lang_name in ("javascript", "typescript", "tsx") and node.type in (
                "function_declaration",
                "class_declaration",
                "method_definition",
            ):
                name = None
                for child in node.children:
                    if child.type == "identifier":
                        name = code[child.start_byte : child.end_byte]
                        break
                if name:
                    results_list.append(
                        {
                            "name": name,
                            "type": node.type.replace("_declaration", "").replace(
                                "_definition", ""
                            ),
                            "line": node.start_point[0] + 1,
                        }
                    )
            for child in node.children:
                visit(child)

        visit(root)
        return results_list

    if os.path.isfile(path):
        ext = os.path.splitext(path)[1]
        results[os.path.basename(path)] = extract_defs_for_file(path, ext)
    elif os.path.isdir(path):
        # Respect .gitignore
        spec = load_gitignore_patterns(path)
        for fname in os.listdir(path):
            fpath = os.path.join(path, fname)
            if os.path.isfile(fpath):
                rel_path = os.path.relpath(fpath, path)
                if spec and spec.match_file(rel_path):
                    continue
                ext = os.path.splitext(fname)[1]
                results[fname] = extract_defs_for_file(fpath, ext)
        if not results:
            results["info"] = "No supported source files found in directory."
    else:
        results["error"] = "Path is neither file nor directory."
    return results
