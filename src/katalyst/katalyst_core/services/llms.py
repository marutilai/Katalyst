from litellm import completion, acompletion
import instructor
import os


def get_llm():
    """Synchronous LiteLLM completion."""
    return completion


def get_llm_async():
    """Asynchronous LiteLLM completion."""
    return acompletion


def get_llm_instructor():
    """Synchronous Instructor-patched LiteLLM client."""
    return instructor.from_litellm(completion)


def get_llm_instructor_async():
    """Asynchronous Instructor-patched LiteLLM client."""
    return instructor.from_litellm(acompletion)


def get_llm_fallbacks():
    """
    Returns a list of fallback LLM models from the KATALYST_LITELLM_FALLBACKS env variable.
    """
    fallbacks = os.getenv("KATALYST_LITELLM_FALLBACKS", "")
    return [m.strip() for m in fallbacks.split(",") if m.strip()]


def get_llm_timeout():
    """
    Returns the LLM timeout in seconds from the KATALYST_LITELLM_TIMEOUT env variable (default 45).
    """
    try:
        return int(os.getenv("KATALYST_LITELLM_TIMEOUT", "45"))
    except Exception:
        return 45
