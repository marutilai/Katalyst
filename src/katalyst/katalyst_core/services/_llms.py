"""
LLM Service Module

Provides simplified API for LLM client access with component-specific configuration.
"""

from litellm import completion, acompletion
import litellm
import instructor
from katalyst.katalyst_core.config import get_llm_config

# Suppress litellm debug info to avoid async task warnings
litellm.suppress_debug_info = True

# Disable async callbacks to prevent pending task warnings
litellm.callbacks = []
litellm.success_callback = []
litellm._async_success_callback = []

# Set to synchronous mode
import os
os.environ["LITELLM_LOG"] = "ERROR"


# New simplified API functions (recommended)
def get_llm_client(component: str, async_mode: bool = False, use_instructor: bool = True):
    """
    Get a configured LLM client for a specific component.
    
    This is the recommended API that handles both client and model selection.
    
    Args:
        component: Component name (e.g., 'planner', 'agent_react')
        async_mode: Whether to return async client
        use_instructor: Whether to wrap with instructor
        
    Returns:
        Configured LLM client
    """
    if async_mode:
        client = acompletion
        if use_instructor:
            client = instructor.from_litellm(acompletion)
    else:
        client = completion
        if use_instructor:
            client = instructor.from_litellm(completion)
    
    return client


def get_llm_params(component: str) -> dict:
    """
    Get LLM parameters for a specific component.
    
    Args:
        component: Component name
        
    Returns:
        Dictionary with model, timeout, fallbacks, and other parameters
    """
    config = get_llm_config()
    params = {
        "model": config.get_model_for_component(component),
        "timeout": config.get_timeout(),
        "temperature": 0.3,  # Default temperature
        "fallbacks": config.get_fallback_models(),
    }
    
    # Add api_base if available (for Ollama and other local providers)
    api_base = config.get_api_base()
    if api_base:
        params["api_base"] = api_base
    
    return params


