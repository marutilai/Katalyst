from litellm import completion, acompletion
import instructor


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
