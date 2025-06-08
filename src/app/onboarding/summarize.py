"""
Summarization utilities for onboarding and documentation generation.
"""


def summarize_text(text, max_length=300):
    """
    Summarize the given text to a maximum length (simple placeholder).
    In production, this could call an LLM or use more advanced logic.
    """
    if len(text) <= max_length:
        return text
    # Simple heuristic: return first and last N lines
    lines = text.splitlines()
    if len(lines) <= 20:
        return "\n".join(lines[:10]) + "\n...\n" + "\n".join(lines[-10:])
    return "\n".join(lines[:5]) + "\n...\n" + "\n".join(lines[-5:])
