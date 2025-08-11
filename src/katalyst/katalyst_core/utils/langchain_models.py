"""
Utility to get native LangChain chat models based on provider configuration.
"""


from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from langchain_litellm import ChatLiteLLMRouter
from langchain_core.language_models import BaseChatModel
from litellm import Router
from typing import Optional,Any
from katalyst.katalyst_core.utils.logger import get_logger
from pydantic import BaseModel
import os
logger = get_logger()


def get_provider_for_model_name(model_name: str) -> Optional[str]:
    """
    Given a model name, return the provider string.
    E.g., "gpt-3.5-turbo" -> "openai", "claude-3-opus-20240229" -> "anthropic", etc.
    Returns None if provider cannot be determined.
    """
    if not model_name:
        return None
    model_name = model_name.lower()
    if "gpt" in model_name or "openai" in model_name:
        return "openai"
    if "claude" in model_name or "anthropic" in model_name:
        return "anthropic"
    if "mistral" in model_name:
        return "mistral"
    if "llama" in model_name or "llama-2" in model_name or "llama-3" in model_name:
        return "ollama"
    if "gemini" in model_name or "palm" in model_name or "google" in model_name:
        return "google"
    if "azure" in model_name:
        return "azure"
    if "cohere" in model_name:
        return "cohere"
    if "ollama" in model_name:
        return "ollama"
    # Add more providers as needed
    return None

# An LLM Wrapper with Retry Logic Built in
class RetryChatLiteLLMRouter(ChatLiteLLMRouter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _convert_tool_choice(self, tool_choice):
        """Convert LangChain tool_choice values to OpenAI-compatible values"""
        if tool_choice == "any":
            return "auto"  # Convert 'any' to 'auto' for OpenAI compatibility
        return tool_choice

    def _validate_and_return_structured_response(
        self, response: Any, response_format: BaseModel
    ) -> BaseModel:
        """Validate and return structured response"""
        try:
            if hasattr(response, "content"):
                logger.debug(f"Response: {response}")
                content = response.content
            else:
                content = str(response)
            # For models with native support, try direct validation first
            try:
                return response_format.model_validate_json(content)
            except Exception:
                logger.debug(
                    f"Direct validation failed, falling back to extraction for model {getattr(self, 'model', '')}, response content: {content}"
                )

        except Exception as e:
            logger.error(f"Failed to validate structured response: {e}")
            logger.error(f"Response content: {content[:500]}...")
            raise ValueError(f"Failed to parse structured response: {e}")
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(30),
        retry=retry_if_exception_type(lambda exc: isinstance(exc, Exception) and not isinstance(exc, getattr(__import__('katalyst.katalyst_core.utils.exceptions', fromlist=['UserInputRequiredException']), 'UserInputRequiredException', Exception))),
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
            f"[Retry] Retrying invoke due to: {retry_state.outcome.exception() if retry_state.outcome else 'unknown error'} (attempt {retry_state.attempt_number})"
        ),
    )
    def invoke(self, *args, **kwargs):
        # Handle structured output
        response = super().invoke(*args, **kwargs)
        response_format = kwargs.pop("response_format", None)
        if response_format:
            return self._validate_and_return_structured_response(response, response_format)
        return response

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(30),
        retry=retry_if_exception_type(lambda exc: isinstance(exc, Exception) and not isinstance(exc, getattr(__import__('katalyst.katalyst_core.utils.exceptions', fromlist=['UserInputRequiredException']), 'UserInputRequiredException', Exception))),
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
            f"[Retry] Retrying invoke due to: {retry_state.outcome.exception() if retry_state.outcome else 'unknown error'} (attempt {retry_state.attempt_number})"
        ),
    )
    async def ainvoke(self, *args, **kwargs):
        response = await super().ainvoke(*args, **kwargs)
        return response




def get_litellm_client(model_name:str,use_strictly_one_model:bool=True,**kwargs):
    """Get LLM client, optionally with strict model override"""

    max_tokens_for_claude_35 = 8192
    max_tokens_for_claude_37 = 64000

    # get temprature from kwargs
    temperature = kwargs.pop("temperature", 0)
    # get provider for model name
    provider = get_provider_for_model_name(model_name)
    if provider is None:
        raise ValueError(f"Unsupported model: {model_name}")
    if use_strictly_one_model:
        if provider == "azure":
            strict_model_list = [
                {
                    "model_name": model_name,
                    "litellm_params": {
                        "model": model_name,
                        "temperature": temperature,
                        "api_base": os.getenv("AZURE_OPENAI_ENDPOINT"),
                        "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
                        "api_version": os.getenv("AZURE_OPENAI_VERSION"),
                    },
                }
            ]
        # Anthropic models need to have max_tokens defined as integer
        elif provider == "anthropic":
            # For anthropic claude-35 models the max_completion tokens are 8192 and that is the default as well.
            if "claude-3-5" in model_name:
                strict_model_list = [
                    {
                        "model_name": model_name,
                        "litellm_params": {
                            "model": model_name,
                            "temperature": temperature,
                            "max_completion_tokens": max_tokens_for_claude_35,
                        },
                    }
                ]
            else:
                # For anthropic claude-37 models the max_completion tokens are 64000 , but the default is 8192 so we need to override this default value
                strict_model_list = [
                    {
                        "model_name": model_name,
                        "litellm_params": {
                            "model": model_name,
                            "temperature": temperature,
                            "max_completion_tokens": max_tokens_for_claude_37,
                        },
                    }
                ]
        else:
            # gpt models have by default `None` as max_completion_tokens which defaults to max_tokens possible in completion
            strict_model_list = [
                {
                    "model_name": model_name,
                    "litellm_params": {
                        "model": model_name,
                        "temperature": temperature,
                    },
                }
            ]
        strict_router = Router(model_list=strict_model_list)
        return RetryChatLiteLLMRouter(
            router=strict_router,
            model=model_name,
        )
    else:
        # if there is no policy on using strictly one mode ,
        #  then we create use the first "model" as provided one and then we implemet fallback policy 
        # TODO: Add this section
        raise NotImplementedError("Fallback model logic is not yet implemented.")

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
## Usage 
class DummyResponse(BaseModel):
    response: str

if __name__ == "__main__":
    
    llm = get_litellm_client("claude-3-5-sonnet-20240620")
    # usage with sync invoke 
    print(llm.invoke(input=[
        {
            "role": "system",
            "content": "You are a helpful assistant that can answer questions about the capital of France."
        },
        {
            "role": "user",
            "content": "What is the capital of France?"
        }
    ],response_format=DummyResponse).response)