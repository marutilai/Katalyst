from typing import Dict
from katalyst_agent.utils.logger import get_logger
from katalyst_agent.utils.tools import katalyst_tool
from katalyst_agent.services.code_structure import extract_code_definitions


@katalyst_tool
def list_code_definition_names(path: str, auto_approve: bool = False) -> str:
    """
    Lists code definitions (classes, functions, methods) from a source file or files in a directory using the tree-sitter-languages package.
    Supports Python, JavaScript, TypeScript, and TSX source files. No manual grammar setup is required.
    """
    logger = get_logger()
    logger.info(f"Entered list_code_definition_names with path: {path}, auto_approve: {auto_approve}")
    results = extract_code_definitions(path)
    if 'error' in results:
        return f"""
<list_code_definition_names>
<error>{results['error']}</error>
</list_code_definition_names>"""
    if 'info' in results:
        return f"""
<list_code_definition_names>
<info>{results['info']}</info>
</list_code_definition_names>"""
    xml = ["<list_code_definition_names>"]
    for fname, defs in results.items():
        xml.append(f"  <file name=\"{fname}\">")
        if not defs:
            xml.append("    <info>No definitions found.</info>")
        else:
            for d in defs:
                if 'error' in d:
                    xml.append(f"    <error>{d['error']}</error>")
                else:
                    xml.append(f"    <definition type=\"{d['type']}\" line=\"{d['line']}\">{d['name']}</definition>")
        xml.append("  </file>")
    xml.append("</list_code_definition_names>")
    logger.info("Exiting list_code_definition_names")
    return '\n'.join(xml)
