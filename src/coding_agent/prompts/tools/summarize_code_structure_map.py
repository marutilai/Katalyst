"""
Summarize the purpose and main components of the following code file. Return a JSON object with:
- file_path: str (the file being summarized)
- summary: str (a concise summary of the file's purpose and main logic)
- key_classes: list[str] (names of important classes, if any)
- key_functions: list[str] (names of important functions, if any)
"""

MAP_PROMPT = """
You are a codebase documentation assistant.
Given the contents of a code file, write a concise summary of its purpose, main logic, and key components.
Identify and list any important classes and functions.
Respond in the following JSON format:
{"file_path": "...", "summary": "...", "key_classes": [...], "key_functions": [...]}.
Code file contents:
{context}
"""
