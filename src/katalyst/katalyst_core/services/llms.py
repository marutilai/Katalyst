from litellm import completion, acompletion
import instructor
import os


def get_llm_model_for_component(component_name: str) -> str:
    """
    Selects an LLM model based on the component's purpose.

    - 'planner' or 'replanner': Uses KATALYST_REASONING_MODEL for high-level planning.
    - 'agent_react' (or default): Uses KATALYST_EXECUTION_MODEL for execution.
    """
    component_name = component_name.lower()
    if component_name == "planner" or component_name == "replanner":
        return os.getenv("KATALYST_REASONING_MODEL", "gpt-4.1")

    # Default model for 'agent_react' and any other components
    return os.getenv("KATALYST_EXECUTION_MODEL", "gpt-4.1-mini")


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
    Returns a list of fallback LLM models from the KATALYST_LLM_MODEL_FALLBACK env variable.
    """
    fallbacks = os.getenv("KATALYST_LLM_MODEL_FALLBACK", "")
    return [m.strip() for m in fallbacks.split(",") if m.strip()]


def get_llm_timeout():
    """
    Returns the LLM timeout in seconds from the KATALYST_LITELLM_TIMEOUT env variable (default 45).
    """
    try:
        return int(os.getenv("KATALYST_LITELLM_TIMEOUT", "45"))
    except Exception:
        return 45
