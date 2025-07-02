"""
Utility to get native LangChain chat models based on provider configuration.
"""

from typing import Optional
from langchain_core.language_models import BaseChatModel
from katalyst.katalyst_core.utils.logger import get_logger

logger = get_logger()


def get_langchain_chat_model(
    model_name: str,
    provider: str,
    temperature: float = 0,
    timeout: Optional[int] = None,
    api_base: Optional[str] = None,
    **kwargs
) -> BaseChatModel:
    """
    Get a native LangChain chat model based on the provider.
    
    Args:
        model_name: The model name (e.g., "gpt-4", "claude-3-sonnet")
        provider: The provider name (e.g., "openai", "anthropic", "ollama")
        temperature: Temperature for the model
        timeout: Timeout in seconds
        api_base: Optional API base URL
        **kwargs: Additional provider-specific arguments
        
    Returns:
        A LangChain BaseChatModel instance
    """
    
    if provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=model_name,
                temperature=temperature,
                request_timeout=timeout,
                base_url=api_base,
                **kwargs
            )
        except ImportError:
            raise ImportError("Please install langchain-openai: pip install langchain-openai")
            
    elif provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=model_name,
                temperature=temperature,
                timeout=timeout,
                anthropic_api_url=api_base,
                **kwargs
            )
        except ImportError:
            raise ImportError("Please install langchain-anthropic: pip install langchain-anthropic")
            
    elif provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=model_name,
                temperature=temperature,
                base_url=api_base or "http://localhost:11434",
                **kwargs
            )
        except ImportError:
            raise ImportError("Please install langchain-ollama: pip install langchain-ollama")
            
    elif provider == "groq":
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(
                model=model_name,
                temperature=temperature,
                timeout=timeout,
                **kwargs
            )
        except ImportError:
            raise ImportError("Please install langchain-groq: pip install langchain-groq")
            
    elif provider == "together":
        try:
            from langchain_together import ChatTogether
            return ChatTogether(
                model=model_name,
                temperature=temperature,
                **kwargs
            )
        except ImportError:
            raise ImportError("Please install langchain-together: pip install langchain-together")
            
    else:
        raise ValueError(
            f"Unsupported provider: {provider}. "
            "Supported providers: openai, anthropic, ollama, groq, together. "
            "Please install the corresponding langchain package."
        )