"""
Given a set of file summaries, produce an overall summary of the codebase. Return a JSON object with:
- overall_summary: str (a concise summary of the codebase's purpose, architecture, and main components)
- main_components: list[str] (the most important files, classes, or modules)
"""

REDUCE_PROMPT = """
You are a codebase documentation assistant.
Given a list of file summaries, write a concise overall summary of the codebase's purpose, architecture, and main components.
Identify the most important files, classes, or modules.
Respond in the following JSON format:
{"overall_summary": "...", "main_components": [...]}.
File summaries:
{docs}
"""
