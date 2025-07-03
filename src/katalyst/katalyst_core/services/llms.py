"""
LLM Service Module

Provides simplified API for LLM client access with component-specific configuration.
Uses LangChain chat models instead of litellm.
"""

from typing import Optional, Dict, Any
from langchain_core.language_models import BaseChatModel
from katalyst.katalyst_core.config import get_llm_config
from katalyst.katalyst_core.utils.langchain_models import get_langchain_chat_model


def get_llm_client(component: str, async_mode: bool = False, use_instructor: bool = True):
    """
    Get a configured LLM client for a specific component.
    
    This is the recommended API that handles both client and model selection.
    
    Args:
        component: Component name (e.g., 'planner', 'agent_react')
        async_mode: Whether to return async client (not used in LangChain implementation)
        use_instructor: Whether to wrap with instructor (not used in LangChain implementation)
        
    Returns:
        Configured LangChain chat model
    """
    config = get_llm_config()
    model_name = config.get_model_for_component(component)
    provider = config.get_provider()
    api_base = config.get_api_base()
    timeout = config.get_timeout()
    
    # Get the LangChain chat model
    chat_model = get_langchain_chat_model(
        model_name=model_name,
        provider=provider,
        temperature=0.3,
        timeout=timeout,
        api_base=api_base
    )
    
    return chat_model


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